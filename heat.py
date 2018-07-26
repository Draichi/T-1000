from configs.charts import correlation_heatmap
from configs.historical import combined_df
from configs.vars import year

class Lin:
    """Plot correlation heatmap chart"""

    combined_df = combined_df[combined_df.index.year == year]
    combined_df.pct_change().corr(method='pearson')

    correlation_heatmap(
        combined_df.pct_change(),
        "Correlation Heatmap {}".format(year)
    )


    