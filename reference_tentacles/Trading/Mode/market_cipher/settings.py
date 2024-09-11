import typing
import octobot_commons.enums as enums
import octobot_trading.util.config_util as config_util
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    UserInputEditorOptionsTypes,
    UserInputOtherSchemaValuesTypes,
)
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.abstract_mode_base as abstract_mode_base
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils

try:
    import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.activate_managed_order as activate_managed_order
except (ImportError, ModuleNotFoundError):
    activate_managed_order = None

MARKET_CIPHER_SETTINGS_NAME = "market_cipher_settings"
DATA_SOURCE_SETTINGS_NAME = "data_source_settings"
ORDER_SETTINGS_NAME = "order_settings"
DISPLAY_SETTINGS_NAME = "display_settings"

class MarketCipherModeInputs(abstract_mode_base.AbstractBaseMode):
    data_source_settings: utils.DataSourceSettings = None
    display_settings: utils.DisplaySettings = None
    order_settings: utils.LorentzianOrderSettings = None
    market_cipher_settings: utils.MarketCipherSettings = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the trading mode,
        should define all the trading mode's user inputs
        """
        self._init_market_cipher_settings(inputs)
        self._init_order_settings(inputs)
        self._init_data_source_settings(inputs)
        self._init_display_settings(inputs)
        

    def _init_market_cipher_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            MARKET_CIPHER_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="MarketCipherB Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "RobotOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 2,
            },
        )

        Channel_Length = self.UI.user_input(
            "Channel_Length",
            enums.UserInputTypes.INT,
            14,
            inputs,
            # min_val=1,
            # max_val=100,
            title="Channel Length",
            parent_input_name=MARKET_CIPHER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": ""
            },
            order=1,
        )

        Average_Length = self.UI.user_input(
            "Average_Length",
            enums.UserInputTypes.INT,
            5,
            inputs,
            # min_val=1,
            # max_val=100,
            title="Average Length",
            parent_input_name=MARKET_CIPHER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": ""
            },
            order=1,
        )

        MA_Length = self.UI.user_input(
            "MA_Length",
            enums.UserInputTypes.INT,
            10,
            inputs,
            # min_val=1,
            # max_val=100,
            title="MA Length",
            parent_input_name=MARKET_CIPHER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": ""
            },
            order=1,
        )

        is_HeikinAshi = self.UI.user_input(
            "is_HeikinAshi",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            # min_val=1,
            # max_val=100,
            title="use Heikin Ashi",
            parent_input_name=MARKET_CIPHER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": ""
            },
            order=1,
        )

        self.market_cipher_settings = utils.MarketCipherSettings(
            Channel_Length=Channel_Length,
            Average_Length=Average_Length,
            MA_Length=MA_Length,
            is_HeikinAshi=is_HeikinAshi,
        )
        
    def _init_data_source_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            DATA_SOURCE_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Data Source Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                UserInputEditorOptionsTypes.ANT_ICON.value: "DollarOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 10,
            },
        )
        source = self.UI.user_input(
            "candle_source",
            enums.UserInputTypes.OPTIONS,
            enums.PriceStrings.STR_PRICE_CLOSE.value,
            inputs,
            options=[
                enums.PriceStrings.STR_PRICE_CLOSE.value,
                enums.PriceStrings.STR_PRICE_OPEN.value,
                enums.PriceStrings.STR_PRICE_HIGH.value,
                enums.PriceStrings.STR_PRICE_LOW.value,
                "hlc3",
                "ohlc4",
            ],
            title="Candle source",
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
            parent_input_name=DATA_SOURCE_SETTINGS_NAME,
            other_schema_values={"description": "Source of the input data"},
        )
        available_symbols = config_util.get_symbols(self.config, enabled_only=True)
        symbol_settings_by_symbols: typing.Dict[utils.SymbolSettings] = {}
        for symbol in available_symbols:
            this_symbol_data_source_settings = f"data_source_settings_{symbol}"
            self.UI.user_input(
                this_symbol_data_source_settings,
                enums.UserInputTypes.OBJECT,
                None,
                inputs,
                title=f"{symbol} Data Source Settings",
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 4,
                    enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                    enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                },
                parent_input_name=DATA_SOURCE_SETTINGS_NAME,
            )
            trade_on_this_pair: bool = self.UI.user_input(
                f"trade_on_{symbol}",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title=f"Trade on {symbol}",
                parent_input_name=this_symbol_data_source_settings,
                other_schema_values={
                    "description": f"Enable this option to trade on {symbol}"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                },
            )
            this_target_symbol: typing.Optional[str] = None
            inverse_signals: bool = False
            use_custom_pair: bool = False
            enable_long_orders: bool = False
            enable_short_orders: bool = False
            if trade_on_this_pair and len(available_symbols):
                if self.order_settings.enable_long_orders:
                    enable_long_orders: bool = self.UI.user_input(
                        f"enable_long_orders_{symbol}",
                        enums.UserInputTypes.BOOLEAN,
                        True,
                        inputs,
                        title=f"Enable long tading on {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                        },
                    )
                else:
                    enable_long_orders: bool = False
                if self.order_settings.enable_short_orders:
                    enable_short_orders = self.UI.user_input(
                        f"enable_short_orders_{symbol}",
                        enums.UserInputTypes.BOOLEAN,
                        True,
                        inputs,
                        title=f"Enable short tading on {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                        },
                        other_schema_values={
                            enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Note that "
                            "short trading is only working on futures or inversed short tokens"
                        },
                    )
                else:
                    enable_short_orders: bool = False
                inverse_signals = self.UI.user_input(
                    f"inverse_signals_{symbol}",
                    enums.UserInputTypes.BOOLEAN,
                    False,
                    inputs,
                    title=f"Inverse the signals of the strategy for {symbol}",
                    parent_input_name=this_symbol_data_source_settings,
                    other_schema_values={
                        "description": "Sells on long signals and buys on short "
                        "signals. This option can be used to trade short tokens. "
                        "As short tokens will grow in value if the underlying asset "
                        "price decreases."
                    },
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                    },
                )
                use_custom_pair = self.UI.user_input(
                    f"enable_custom_source_{symbol}",
                    enums.UserInputTypes.BOOLEAN,
                    False,
                    inputs,
                    title=f"Use other symbols data to evaluate on {symbol}",
                    parent_input_name=this_symbol_data_source_settings,
                    other_schema_values={
                        "description": f"Enable this option to be able to use another "
                        f"symbols data to trade on {symbol}."
                    },
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                    },
                )
                if use_custom_pair:
                    this_target_symbol = self.UI.user_input(
                        f"{symbol}_target_symbol",
                        enums.UserInputTypes.OPTIONS,
                        self.symbol,
                        inputs,
                        options=available_symbols,
                        title=f"Data source to use for {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        other_schema_values={
                            "description": f"Instead of using {symbol} as a data source"
                            " for the strategy, you can use the data from any other "
                            f"available pair to trade on {symbol}."
                        },
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                        },
                    )
            symbol_settings_by_symbols[symbol] = utils.SymbolSettings(
                symbol=symbol,
                this_target_symbol=this_target_symbol,
                trade_on_this_pair=trade_on_this_pair,
                use_custom_pair=use_custom_pair,
                inverse_signals=inverse_signals,
                enable_long_orders=enable_long_orders,
                enable_short_orders=enable_short_orders,
            )

        self.data_source_settings: utils.DataSourceSettings = utils.DataSourceSettings(
            available_symbols=available_symbols,
            symbol_settings_by_symbols=symbol_settings_by_symbols,
            source=source,
        )

    def _init_order_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            ORDER_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Order Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "ShoppingCartOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 12,
            },
        )
        exit_type = self.UI.user_input(
            "exit_type",
            enums.UserInputTypes.OPTIONS,
            utils.ExitTypes.SWITCH_SIDES,
            inputs,
            options=[
                # utils.ExitTypes.FOUR_BARS,
                # utils.ExitTypes.DYNAMIC,
                utils.ExitTypes.SWITCH_SIDES,
            ],
            title="Exit Type",
            parent_input_name=ORDER_SETTINGS_NAME,
            other_schema_values={
                "description": "Four bars: Exits will occour exactly 4 bars "
                "after the entry. - "
                "Dynamic: attempts to let profits ride by dynamically adjusting "
                "the exit threshold based on kernel regression logic. - "
                "Switch sides: The position will switch sides on each signal.",
            },
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
        )
        if activate_managed_order:
            order_type = self.UI.user_input(
                "order_type",
                enums.UserInputTypes.OPTIONS,
                utils.OrderTypes.REGULAR_ORDER,
                inputs,
                options=[
                    utils.OrderTypes.MANAGED_ORDER,
                    utils.OrderTypes.REGULAR_ORDER,
                ],
                title="Order Type",
                parent_input_name=ORDER_SETTINGS_NAME,
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                },
            )
            uses_managed_order = order_type == utils.OrderTypes.MANAGED_ORDER
        else:
            uses_managed_order = False
        leverage: typing.Optional[int] = None
        if not uses_managed_order:
            if self.exchange_manager.is_future:
                leverage = self.UI.user_input(
                    "leverage",
                    enums.UserInputTypes.INT,
                    1,
                    inputs,
                    min_val=1,
                    max_val=125,
                    title="Leverage",
                    parent_input_name=ORDER_SETTINGS_NAME,
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                    },
                    other_schema_values={
                        enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Leverage to use for futures trades"
                    },
                )
        long_order_volume: typing.Optional[float] = None
        enable_long_orders: bool = self.UI.user_input(
            "enable_long_orders",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Enable long tading",
            parent_input_name=ORDER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
        )
        if enable_long_orders and not uses_managed_order:
            long_order_volume = self.UI.user_input(
                "long_order_size",
                enums.UserInputTypes.TEXT,
                "50%",
                inputs,
                title="Amount to use for long trades",
                parent_input_name=ORDER_SETTINGS_NAME,
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "The "
                    "following syntax is supported: "
                    "1. Percent of total account: '50%' "
                    "2. Percent of availale balance: '50a%' "
                    "3. Flat amount '5' will "
                    "open a 5 BTC trade on BTC/USDT "
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
            )
        enable_short_orders: bool = False
        short_order_volume: typing.Optional[float] = None
        # if self.exchange_manager.is_future:
        enable_short_orders = self.UI.user_input(
            "enable_short_orders",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Enable short tading",
            parent_input_name=ORDER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Note that "
                "short trading is only working on futures or inversed short tokens"
            },
        )
        if enable_short_orders and not uses_managed_order:
            short_order_volume = self.UI.user_input(
                "short_order_size",
                enums.UserInputTypes.TEXT,
                "50%",
                inputs,
                title="Amount to use for short trades",
                parent_input_name=ORDER_SETTINGS_NAME,
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "The "
                    "following syntax is supported: "
                    "1. Percent of total account: '50%' "
                    "2. Percent of availale balance: '50a%' "
                    "3. Flat amount '5' will "
                    "open a 5 BTC trade on BTC/USDT "
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
            )
        self.order_settings: utils.LorentzianOrderSettings = (
            utils.LorentzianOrderSettings(
                enable_short_orders=enable_short_orders,
                short_order_volume=short_order_volume,
                long_order_volume=long_order_volume,
                enable_long_orders=enable_long_orders,
                leverage=leverage,
                exit_type=exit_type,
                uses_managed_order=uses_managed_order,
            )
        )
    
    def _init_display_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            DISPLAY_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Display Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "LineChartOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 14,
            },
        )
        self.display_settings: utils.DisplaySettings = utils.DisplaySettings(
            show_bar_colors=False,
            show_bar_predictions=False,
            bar_predictions_offset=8,
            use_atr_offset=False,
            enable_additional_plots=False,
            is_backtesting=self.exchange_manager.is_backtesting,
            plotting_mode=self.UI.user_input(
                "plotting_mode",
                enums.UserInputTypes.OPTIONS,
                utils.PlottingModes.REPLOT_MODE,
                inputs,
                options=[
                    utils.PlottingModes.REPLOT_MODE,
                    utils.PlottingModes.PLOT_RECORDING_MODE,
                ],
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Replot "
                    "history mode will overwrite the existing plots on each bar close "
                    "and when you change settings. While plot recording mode will only "
                    "add to the plotting history on each bar close. "
                },
                title="Plotting Mode",
                parent_input_name=DISPLAY_SETTINGS_NAME,
            )
        )