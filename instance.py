from config.charts import df_scatter
from historical import combined_df

class BotAdvisor:
    def __init__(self):
        self.data = []
    
    def chart(separate_y_axis, y_axis_label, scale):
        df_scatter(
            combined_df,
            'logarithm PRICES (USD)',
            separate_y_axis=separate_y_axis,
            y_axis_label=y_axis_label,
            scale=scale
        )
    
    chart(False, 'Test', 'linear')

    