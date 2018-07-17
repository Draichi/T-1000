import os, pickle, quandl
import numpy as np
import pandas as pd
from config.functions import *
from config.charts import *
# --------------------------------------------------------------->
# data source:
# https://blog.quandl.com/api-for-bitcoin-data

# --------------------------------------------------------------->
# gettin pricing data for 3more BTC exchanges
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
# btc_usd_datasets['MEAN_PRICE'] = btc_usd_datasets.mean(axis=1)
# uncomment the folowing to see the merged data
# print(btc_usd_df.tail())
# quit()
# --------------------------------------------------------------->
# generate a scatter plot of the entire dataframe

#------------------------------------------------------------->
altcoin_data ={}
for altcoin in altcoins:
    coinpair = 'BTC_{}'.format(altcoin)
    altcoin_data[altcoin] = get_crypto_data(coinpair)
    
for altcoin in altcoin_data.keys():
    altcoin_data[altcoin]['Price_USD'] = altcoin_data[altcoin]['weightedAverage'] * btc_usd_df['Weighted Price']

# print(list(altcoin_data['ETH']['Price_USD']))
# quit()
# merge USD price of each altcoin into single dataframe
combined_df = merge_dfs_on_column(list(altcoin_data.values()), list(altcoin_data.keys()), 'Price_USD')
# add BTC price to the dataframe
combined_df['BTC'] = btc_usd_df['Weighted Price']

combined_df_2016 = combined_df[combined_df.index.year == 2016]
combined_df_2016.pct_change().corr(method='pearson')

combined_df_2017 = combined_df[combined_df.index.year == 2017]
combined_df_2017.pct_change().corr(method='pearson')

combined_df_2018 = combined_df[combined_df.index.year == 2018]
combined_df_2018.pct_change().corr(method='pearson')

correlation_heatmap(combined_df_2018.pct_change(), "Correlation 2018")
df_scatter(
    combined_df,
    'logarithm PRICES (USD)',
    separate_y_axis=False,
    y_axis_label='Coin Value (USD)',
    scale='log'
)
# combined_df.to_csv('datasets/altcoins_joined_closes_20181405_.csv')