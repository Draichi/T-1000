from configs.charts import df_scatter
from configs.historical import combined_df
from configs.vars import separate_y_axis

class Log:
    """Plot historical logarithm chart"""
    df_scatter(
        combined_df,
        'Historical Logarithm Altcoins Price',
        separate_y_axis,
        'Price USD',
        'log',
        False
    )

    