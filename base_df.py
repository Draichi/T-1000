import pandas as pd
from configs.functions import get_quandl_data
from configs.charts import correlation_heatmap
import datetime

coins = ['giant', 'rupaya', 'hush', 'fantasy-gold', 'ethereum', 'bitcoin', 'litecoin', 'monero']
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day

def get_coin_data(coin):
    df = pd.read_csv('datasets/df_{}-{}-{}.csv'.format(coin, todays_day, todays_month))
    return df

base_df = get_coin_data('bitcoin')

for coin in coins:
    df = get_coin_data(coin)
    base_df[coin] = df[coin]

base_df.set_index('date', inplace=True)
base_df.pct_change().corr(method='pearson')
base_df.to_csv('datasets/base_df-{}-{}.csv'.format(todays_day, todays_month))

correlation_heatmap(base_df.pct_change(), "Correlation base_df")