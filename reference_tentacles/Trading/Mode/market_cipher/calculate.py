import numpy
import numpy.typing as npt
import talib

import octobot_commons.enums as enums
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting

import tentacles.Trading.Mode.market_cipher.trade_execution as trade_execution
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.plottings.plots as matrix_plots
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.abstract_producer_base as abstract_producer_base
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.producer_base as producer_base

try:
    from tentacles.Evaluator.Util.candles_util import CandlesUtil
except (ModuleNotFoundError, ImportError) as error:
    raise RuntimeError("CandlesUtil tentacle is required to use HLC3 and HikenAshi") from error

def normalize(
    src: npt.NDArray[numpy.float64],
    #   _min: float, _max: float
):
    # normalizes to values from 0 -1
    min_val = numpy.min(src)
    return (src - min_val) / (numpy.max(src) - min_val)

    # return _min + (_max - _min) * (src - numpy.min(src)) / numpy.max(src)



@staticmethod
def HeikinAshi(candles_open, candles_high, candles_low, candles_close):
    """
    محاسبه آرایه‌های Heikin Ashi برای شمع‌های داده شده
    :param candles_open: لیست قیمت‌های باز شدن
    :param candles_high: لیست قیمت‌های بالا
    :param candles_low: لیست قیمت‌های پایین
    :param candles_close: لیست قیمت‌های بسته شدن
    :return: HAopen, HAhigh, HAlow, HAclose
    """
    haOpen = numpy.zeros_like(candles_open)
    haHigh = numpy.zeros_like(candles_high)
    haLow = numpy.zeros_like(candles_low)
    haClose = numpy.zeros_like(candles_close)

    for i in range(len(candles_open)):
        if i == 0:
            haOpen[i] = candles_open[i]
            haClose[i] = numpy.mean([candles_open[i], candles_high[i], candles_low[i], candles_close[i]])
        else:
            haOpen[i] = (haOpen[i-1] + haClose[i-1]) / 2
            haClose[i] = numpy.mean([candles_open[i], candles_high[i], candles_low[i], candles_close[i]])
            
        haHigh[i] = max(candles_high[i], haOpen[i], haClose[i])
        haLow[i] = min(candles_low[i], haOpen[i], haClose[i])

    return haOpen, haHigh, haLow, haClose

class MarketCipherScript(
    abstract_producer_base.AbstractBaseModeProducer,
    producer_base.MatrixProducerBase,
    trade_execution.CipherTradeExecution,
):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        abstract_producer_base.AbstractBaseModeProducer.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        producer_base.MatrixProducerBase.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        self.start_long_trades_cache: dict = {}
        self.start_short_trades_cache: dict = {}

    def n_wt(self, _hlc3: npt.NDArray[numpy.float64], cipher_settings):
        channel_length = int(cipher_settings.Channel_Length)
        avg_length = int(cipher_settings.Average_Length)
        ma_length = int(cipher_settings.MA_Length)

        # Set TA-Lib compatibility mode to match Pine Script behavior
        talib.set_compatibility(1)
        # Calculate EMA of candle (equivalent to esa in Pine Script)
        esa = talib.EMA(_hlc3, timeperiod=channel_length)
        # Calculate DE (absolute difference between candle and esa)
        de = talib.EMA(abs(_hlc3 - esa), timeperiod=channel_length)
        # Calculate CI with zero division handling
        ci = (_hlc3[1:] - esa[1:]) / (0.015 * de[1:])
        # Calculate WT1 and WT2
        wt1 = talib.EMA(ci, timeperiod=avg_length)
        # Reset TA-Lib compatibility mode
        talib.set_compatibility(0)
        wt2 = talib.SMA(wt1, timeperiod=ma_length)
        

        # esa = tulipy.ema(_hlc3, channel_length)
        # de = tulipy.ema(abs(_hlc3 - esa), channel_length)
        # ci = (_hlc3[1:] - esa[1:]) / (0.015 * de[1:])
        # wt1 = tulipy.ema(ci, avg_length)  # tci
        # wt2 = tulipy.sma(wt1, ma_length)


        wt1, wt2 = basic_utilities.cut_data_to_same_len((wt1, wt2))
        # wt1 = normalize(wt1)
        # wt2 = normalize(wt2)

        self.logger.info('input')
        self.logger.warning(_hlc3)
        self.logger.info('esa')
        self.logger.warning(esa)
        # self.logger.info('ema2')
        # self.logger.warning(ema2)
        # self.logger.info('ci')
        self.logger.warning(ci)

        # Crossovers
        buy, sell = utils.get_is_crossing_data(
            wt1, wt2
        )
        
        return buy, sell


    async def evaluate_market_cipher(
        self,
        ctx: context_management.Context,
    ):
        this_symbol_settings: utils.SymbolSettings = (
            self.trading_mode.data_source_settings.symbol_settings_by_symbols[
                self.trading_mode.symbol
            ]
        )
        await self.init_order_settings(
            ctx, leverage=self.trading_mode.order_settings.leverage
        )
        if not this_symbol_settings.trade_on_this_pair:
            return

        if await self._trade_cached_backtesting_candles_if_available(ctx):
            return
        s_time = basic_utilities.start_measure_time(
            f" Market Cipher {self.trading_mode.symbol} -"
        )

        data_source_symbol: str = this_symbol_settings.get_data_source_symbol_name()
        (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
            candle_times,
        ) = await self._get_candle_data(
            ctx,
            candle_source_name=self.trading_mode.data_source_settings.source,
            data_source_symbol=data_source_symbol,
            heikinashi=self.trading_mode.market_cipher_settings.is_HeikinAshi,
        )

        buy, sell = self.n_wt(user_selected_candles, self.trading_mode.market_cipher_settings)

        # cut all historical data to same length
        # for numpy and loop indizies being aligned
        (
            candle_closes,
            candle_highs,
            candle_lows,
            candle_times,
            candles_hlc3,
            user_selected_candles,
            buy, sell,
        ) = basic_utilities.cut_data_to_same_len(
            (
                candle_closes,
                candle_highs,
                candle_lows,
                candle_times,
                candles_hlc3,
                user_selected_candles,
                buy, sell,
            )
        )

        cutted_data_length: int = len(buy)
        if (
            not self.exchange_manager.is_backtesting
            and self.trading_mode.display_settings.is_plot_recording_mode
        ):
            max_bars_back_index: int = (
                cutted_data_length - 200 if cutted_data_length > 200 else 0
            )
        else:
            max_bars_back_index: int = 0
        
        # cutted_data_length: int = 200
        # max_bars_back_index: int = 0


        # =================================
        # ==== Next Bar Classification ====
        # =================================

        # This model specializes specifically in predicting the direction of price
        # action over the course of the next classification_settings.only_train_on_every_x_bars.

        previous_signals: list = [utils.SignalDirection.neutral]
        historical_predictions: list = []
        # bars_since_red_entry: int = 5  # dont trigger exits on loop start
        # bars_since_green_entry: int = 5  # dont trigger exits on loop start

        start_long_trades: list = []
        start_short_trades: list = []
        exit_short_trades: list = []
        exit_long_trades: list = []
        is_buy_signals: list = []
        is_sell_signals: list = []

        basic_utilities.end_measure_time(
            s_time,
            f" Market Cipher {self.trading_mode.symbol} - calculating full history indicators",
        )
        s_time = basic_utilities.start_measure_time(
            f" Market Cipher {self.trading_mode.symbol} - classifying candles"
        )

        for candle_index in range(max_bars_back_index, cutted_data_length):
            
            signal = (
                utils.SignalDirection.long
                if buy[candle_index]
                else (
                    utils.SignalDirection.short
                    if sell[candle_index]
                    else previous_signals[-1]
                )
            )
            is_different_signal_type: bool = previous_signals[-1] != signal
            previous_signals.append(signal)

            # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
            # is_early_signal_flip = previous_signals[-1] and (
            #     previous_signals[-2] or previous_signals[-3] or previous_signals[-4]
            # )
            is_buy_signal = (
                signal == utils.SignalDirection.long
            )
            is_buy_signals.append(is_buy_signal)
            is_sell_signal = (
                signal == utils.SignalDirection.short
            )
            is_sell_signals.append(is_sell_signal)

            is_new_buy_signal = is_buy_signal and is_different_signal_type
            is_new_sell_signal = is_sell_signal and is_different_signal_type

            # ===========================
            # ==== Entries and Exits ====
            # ===========================

            # Entry Conditions: Booleans for ML Model Position Entries
            exit_short_trade = (
                is_new_buy_signal
            )
            exit_short_trades.append(exit_short_trade)
            start_long_trade = (
                is_new_buy_signal
            )
            start_long_trades.append(start_long_trade)
            exit_long_trade = (
                is_new_sell_signal
            )
            exit_long_trades.append(exit_long_trade)
            start_short_trade = (
                is_new_sell_signal
            )
            start_short_trades.append(start_short_trade)

            # exits

            # utils.ExitTypes.SWITCH_SIDES doesnt need exits

        if ctx.exchange_manager.is_backtesting:
            self._cache_backtesting_signals(
                symbol=self.trading_mode.symbol,
                ctx=ctx,
                s_time=s_time,
                candle_times=candle_times,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        else:
            basic_utilities.end_measure_time(
                s_time,
                f" Market Cipher {self.trading_mode.symbol} -"
                " classifying candles",
            )
            await self.trade_live_candle(
                ctx=ctx,
                order_settings=self.trading_mode.order_settings,
                symbol=self.trading_mode.symbol,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        s_time = basic_utilities.start_measure_time()
        await self._handle_plottings(
            ctx=ctx,
            this_symbol_settings=this_symbol_settings,
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_times=candle_times,
            candles_hlc3=candles_hlc3,
            candles_ohlc4=candles_ohlc4,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            # previous_signals=previous_signals,
            # is_buy_signals=is_buy_signals,
            # is_sell_signals=is_sell_signals,
        )
        basic_utilities.end_measure_time(
            s_time,
            f" Market Cipher {self.trading_mode.symbol} - storing plots",
        )

    async def _handle_plottings(
        self,
        ctx: context_management.Context,
        this_symbol_settings: utils.SymbolSettings,
        candle_closes: npt.NDArray[numpy.float64],
        candle_highs: npt.NDArray[numpy.float64],
        candle_lows: npt.NDArray[numpy.float64],
        candle_times: npt.NDArray[numpy.float64],
        candles_hlc3: npt.NDArray[numpy.float64],
        candles_ohlc4: npt.NDArray[numpy.float64],
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
    ) -> None:
        slightly_below_lows: npt.NDArray[numpy.float64] = candle_lows * 0.999
        slightly_above_highs: npt.NDArray[numpy.float64] = candle_highs * 1.001
        # use_own_y_axis: bool = this_symbol_settings.use_custom_pair
        cache_key_prefix: str = "b-" if self.exchange_manager.is_backtesting else "l-"

        await self._handle_short_history_plottings(
            ctx=ctx,
            cache_key_prefix=cache_key_prefix,
            candle_times=candle_times,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            slightly_below_lows=slightly_below_lows,
            slightly_above_highs=slightly_above_highs,
        )

    async def _handle_short_history_plottings(
        self,
        ctx: context_management.Context,
        cache_key_prefix: str,
        candle_times: npt.NDArray[numpy.float64],
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
        slightly_below_lows: npt.NDArray[numpy.float64],
        slightly_above_highs: npt.NDArray[numpy.float64],
    ) -> None:
        await matrix_plots.plot_conditional(
            ctx=ctx,
            is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
            title="Start Long Trades",
            signals=start_long_trades,
            values=slightly_below_lows,  # Slightly below the closing price
            times=candle_times,
            value_key=f"{cache_key_prefix}st-l",
            color="green",
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
            title="Start Short Trades",
            signals=start_short_trades,
            values=slightly_above_highs,
            times=candle_times,
            value_key=f"{cache_key_prefix}st-s",
            color="red",
        )
        has_exit_signals = len(exit_short_trades) and len(exit_long_trades)
        if has_exit_signals:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Exit Long Trades",
                signals=exit_long_trades,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}ex-l",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Exit Short Trades",
                signals=exit_short_trades,
                values=slightly_below_lows,  # Slightly below the closing price
                times=candle_times,
                value_key=f"{cache_key_prefix}ex-s",
            )

    async def _get_candle_data(
        self,
        ctx: context_management.Context,
        candle_source_name: str,
        data_source_symbol: str,
        heikinashi: bool = False,
    ) -> tuple:
        max_history = True if ctx.exchange_manager.is_backtesting else False
        candle_times = await exchange_public_data.Time(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_opens = await exchange_public_data.Open(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_closes = await exchange_public_data.Close(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_highs = await exchange_public_data.High(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_lows = await exchange_public_data.Low(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        
        if heikinashi:
            candle_opens, candle_highs, candle_lows, candle_closes = HeikinAshi(
                candle_opens,
                candle_highs,
                candle_lows,
                candle_closes,
            )

        candles_hlc3 = CandlesUtil.HLC3(
            candle_highs,
            candle_lows,
            candle_closes,
        )
        candles_ohlc4 = CandlesUtil.OHLC4(
            candle_opens,
            candle_highs,
            candle_lows,
            candle_closes,
        )

        user_selected_candles = None
        if candle_source_name == enums.PriceStrings.STR_PRICE_CLOSE.value:
            user_selected_candles = candle_closes
        if candle_source_name == enums.PriceStrings.STR_PRICE_OPEN.value:
            user_selected_candles = await exchange_public_data.Open(
                ctx, symbol=data_source_symbol, max_history=max_history
            )
        if candle_source_name == enums.PriceStrings.STR_PRICE_HIGH.value:
            user_selected_candles = candle_highs
        if candle_source_name == enums.PriceStrings.STR_PRICE_LOW.value:
            user_selected_candles = candle_lows
        if candle_source_name == "hlc3":
            user_selected_candles = candles_hlc3
        if candle_source_name == "ohlc4":
            user_selected_candles = candles_ohlc4
        return (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
            candle_times,
        )

