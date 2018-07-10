import os, pickle, quandl
import numpy as np
import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go
import plotly.figure_factory as ff
from config import *
from functions.functions import *
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
btc_usd_datasets.replace(0, np.nan, inplace=True)
btc_usd_datasets['MEAN_PRICE'] = btc_usd_datasets.mean(axis=1)
# uncomment the folowing to see the merged data
#btc_usd_datasets.tail()
# --------------------------------------------------------------->
# generate a scatter plot of the entire dataframe
def df_scatter(df,
                title,
                separate_y_axis=False,
                y_axis_label='',
                scale='linear',
                initial_hide=False
               ):
        label_arr = list(df)
        series_arr = list(map(lambda col: df[col], label_arr))
        
        layout = go.Layout(
            plot_bgcolor='#010008',
            paper_bgcolor='#010008',
            title=title,
            legend=dict(orientation="h"),
            xaxis=dict(type='date'),
            yaxis=dict(
                title=y_axis_label,
                showticklabels= not separate_y_axis,
                type=scale
            )
        )
        y_axis_config = dict(
            overlaying='y',
            showticklabels=False,
            type=scale
        )
        visibility = 'visible'
        if initial_hide:
            visibility = 'legendonly'
        # form trace for each series
        trace_arr = []
        for index, series in enumerate(series_arr):
            trace = go.Scatter(
                x=series.index,
                y=series,
                name=label_arr[index],
                visible=visibility
            )
            # add separate axis
            if separate_y_axis:
                trace['yaxis'] = 'y{}'.format(index + 1)
                layout['yaxis{}'.format(index + 1)] = y_axis_config
            
            trace_arr.append(trace)
        offline.plot(
            {
                'data': trace_arr, 
                'layout': layout
            }, 
            image = None,
            filename = '{}.html'.format(title.replace(" ", "_")),
            image_filename = title
        )
#------------------------------------------------------------->
altcoin_data ={}
for altcoin in altcoins:
    coinpair = 'BTC_{}'.format(altcoin)
    crypto_price_df = get_crypto_data(coinpair)
    altcoin_data[altcoin] = crypto_price_df
    
for altcoin in altcoin_data.keys():
    altcoin_data[altcoin]['Price_USD'] = altcoin_data[altcoin]['weightedAverage'] * btc_usd_datasets['MEAN_PRICE']
    
# merge USD price of each altcoin into single dataframe
combined_df = merge_dfs_on_column(list(altcoin_data.values()), list(altcoin_data.keys()), 'Price_USD')

# add BTC price to the dataframe
combined_df['BTC'] = btc_usd_datasets['MEAN_PRICE']

# scale can be 'linear' or 'log'
# df_scatter(combined_df,
#            'CRYPTO PRICES (USD)',
#            separate_y_axis=False,
#            y_axis_label='Coin Value (USD)',
#            scale='log')

combined_df_2016 = combined_df[combined_df.index.year == 2016]
combined_df_2016.pct_change().corr(method='pearson')

combined_df_2017 = combined_df[combined_df.index.year == 2017]
combined_df_2017.pct_change().corr(method='pearson')

combined_df_2018 = combined_df[combined_df.index.year == 2018]
combined_df_2018.pct_change().corr(method='pearson')

def correlation_heatmap(df, title, absolute_bounds=True):
    '''plot a correlation heatmap for the entire dataframe'''
    heatmap = go.Heatmap(
        z=df.corr(method='pearson').values,
        x=df.columns,
        y=df.columns,
        colorbar=dict(title='Pearson Coefficient')
    )
    layout = go.Layout(title=title)
    
    if absolute_bounds:
        heatmap['zmax'] = 1.0
        heatmap['zmin'] = -1.0
    
    offline.plot(
        {
            'data': [heatmap], 
            'layout': layout
        }, 
        image = None,
        filename = '{}.html'.format(title.replace(" ", "_")),
        image_filename = title
    )

correlation_heatmap(combined_df_2018.pct_change(), "Correlation 2018")
df_scatter(
    combined_df,
    'logarithm PRICES (USD)',
    separate_y_axis=False,
    y_axis_label='Coin Value (USD)',
    scale='log'
)
combined_df.to_csv('datasets/altcoins_joined_closes_20181405_.csv')