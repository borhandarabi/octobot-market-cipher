async def script(ctx):
    try:
        from tentacles.Meta.Keywords.matrix_library.RunAnalysis.AnalysisMode import (
            DefaultRunAnalysisMode,
        )

        return await DefaultRunAnalysisMode().run_analysis_script(ctx)
    except (ImportError, ModuleNotFoundError):
        pass
