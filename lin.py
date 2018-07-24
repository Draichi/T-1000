from config.charts import df_scatter
from config.historical import combined_df
from config.vars import separate_y_axis

class Lin:
    """Plot historical chart"""
    df_scatter(
        combined_df, 
        'Historical Altcoins Price',
        separate_y_axis,
        'Price USD',
        'linear',
        False
    )

    