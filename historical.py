import os, pickle, quandl
import numpy as np
import pandas as pd
from config.functions import *
from config.charts import *



# este so usa bitstamp
exchange_data = {}
for exchange in exchanges:
    exchange_code = 'BCHARTS/{}USD'.format(exchange)
    btc_exchange_df = get_quandl_data(exchange_code)
    exchange_data[exchange] = btc_exchange_df
# --------------------------------------------------------------->
# merge a single column of each dataframe

# --------------------------------------------------------------->
# merge BTC price dataseries into a single dataframe
btc_usd_datasets = merge_dfs_on_column(
    list(exchange_data.values()),
    list(exchange_data.keys()),
    'Weighted Price'
)

btc_usd_df = get_quandl_data('BCHARTS/BITSTAMPUSD')

btc_usd_df.replace(0, np.nan, inplace=True)
# btc

altcoin_data ={}
for altcoin in altcoins:
    coinpair = 'BTC_{}'.format(altcoin)
    altcoin_data[altcoin] = get_crypto_data(coinpair)
    
for altcoin in altcoin_data.keys():
    altcoin_data[altcoin]['Price_USD'] = altcoin_data[altcoin]['weightedAverage'] * btc_usd_df['Weighted Price']


combined_df = merge_dfs_on_column(list(altcoin_data.values()), list(altcoin_data.keys()), 'Price_USD')
# add BTC price to the dataframe
combined_df['BTC'] = btc_usd_df['Weighted Price']
