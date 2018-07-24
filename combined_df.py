import pandas as pd
import numpy as np
from config.functions import merge_dfs_on_column, get_quandl_data
coins = ['giant','ethereum']

def get_coin_data(coin):
    df = pd.read_csv('df_{}-21-7.csv'.format(coin))
    return df

btc_usd_df = get_quandl_data('BCHARTS/BITSTAMPUSD')
btc_usd_df.replace(0, np.nan, inplace=True)
btc_usd_df.reset_index(inplace=True)

coin_data = {}
for coin in coins:
    data = get_coin_data(coin)
    data.set_index('date')
    coin_data[coin] = data
    
for altcoin in coin_data.keys():
    coin_data[altcoin]['Price_USD'] = coin_data[altcoin]['prices'] * btc_usd_df['Weighted Price'] * 1000
    # print('prices',coin_data[altcoin]['prices'])
    # print('usdb',btc_usd_df['Weighted Price'])

combined_df = merge_dfs_on_column(
    list(coin_data.values()),
    list(coin_data.keys()),
    'Price_USD'
)
combined_df['BTC'] = btc_usd_df['Weighted Price']

print(combined_df.tail())
quit()