import pandas as pd
import numpy as np
from config.functions import merge_dfs_on_column, get_quandl_data
from config.charts import correlation_heatmap

coins = ['giant', 'rupaya', 'hush', 'fantasy-gold', 'ethereum', 'bitcoin', 'litecoin', 'monero']

def get_coin_data(coin):
    df = pd.read_csv('df_{}-24-7.csv'.format(coin))
    return df

base_df = get_coin_data('bitcoin')

for coin in coins:
    df = get_coin_data(coin)
    base_df[coin] = df[coin]

base_df.set_index('date', inplace=True)
base_df.pct_change().corr(method='pearson')

correlation_heatmap(base_df.pct_change(), "Correlation base_df")