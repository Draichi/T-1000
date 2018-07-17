from config.charts import df_scatter
from historical import combined_df
from config.vars import title

class BotAdvisor:
    def __init__(self):
        self.data = []
    
    df_scatter(combined_df, title)

    