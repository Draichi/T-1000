import pandas as pd
import talib
import numpy as np
import requests
import os
import colorama
import plotly.graph_objs as go
import plotly.offline as offline
from plotly import tools
from configs.vars import *
from termcolor import cprint
colorama.init()
# 3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce

symbol_id_dict = {
            'BTC': 1182,
            'ETH': 7605,
            'LTC': 3808,
            'DASH': 3807,
            'XMR': 5038,
            'ETC': 5324,
            'XRP': 5031
        }
#------------------------------------------------------------->
if not (os.path.exists('datasets/apagar.csv')):
    cprint('> downloading', 'yellow', attrs=['bold'])
    headers = {'User-Agent': 'Mozilla/5.0', 'authorization': 'Apikey 3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'}

    # OHLC
    url = 'https://min-api.cryptocompare.com/data/histohour?fsym=BTC&tsym=USD&e=Coinbase&limit=2000'
    response = requests.get(url, headers=headers)
    json_response = response.json()
    result = json_response['Data']
    df1 = pd.DataFrame(result)

    # social
    url = 'https://min-api.cryptocompare.com/data/social/coin/histo/hour?coinId=1182&limit=2000'
    response = requests.get(url, headers=headers)
    json_response = response.json()
    result = json_response['Data']
    df2 = pd.DataFrame(result)

    #merge
    df = pd.merge(df1, df2, on='time')
    df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
    df.drop('time', axis=1, inplace=True)
    # df.set_index('Date', inplace=True)

    close = np.array(df['close'])
    df.loc[:, 'SMA'] = talib.SMA(close)
    df.loc[:, 'MOM_USD'] = talib.MOM(close, timeperiod=14)
    df.loc[:, 'CMO_USD'] = talib.CMO(close, timeperiod=14)
    df.loc[:, 'PPO_BTC'] = talib.PPO(close, fastperiod=12, slowperiod=26, matype=0)
    df.loc[:, 'ROC_BTC'] = talib.ROC(close, timeperiod=10)
    df.loc[:, 'RSI_BTC'] = talib.RSI(close, timeperiod=14)
    df.loc[:, 'STOCHRSI_BTC_K'], df.loc[:, 'STOCHRSI_BTC_D'] = talib.STOCHRSI(close, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)
    df['macd_BTC'], df['macdsignal_BTC'], df['macdhist_BTC'] = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df.fillna(df.mean(), inplace=True)
    df.to_csv('datasets/apagar.csv')
#------------------------------------------------------------->
else:
    cprint('> loading from cache')
    df = pd.read_csv('datasets/apagar.csv')
#------------------------------------------------------------->

INCREASING_COLOR = 'rgb(41, 127, 255)'
DECREASING_COLOR = 'rgb(255, 170, 0)'
# plot 1 dashboard
data = [ dict(
    type = 'candlestick',
    open = df['open'],
    high = df['high'],
    low = df['low'],
    close = df['close'],
    x = df['Date'],
    yaxis = 'y2',
    name = 'Price',
    increasing = dict( line = dict( color = INCREASING_COLOR ) ),
    decreasing = dict( line = dict( color = DECREASING_COLOR ) ),
) ]

layout=dict()

fig = dict( data=data, layout=layout )

fig['layout'] = dict()
fig['layout']['title'] = 'Dashboard 1'
fig['layout']['plot_bgcolor'] = '#2d2929'
fig['layout']['paper_bgcolor'] = '#2d2929'
fig['layout']['font'] = dict(color='rgb(255, 255, 255)', size=17)
fig['layout']['xaxis'] = dict(rangeslider=dict(visible=False), rangeselector=dict(visible=True))
fig['layout']['yaxis'] = dict(domain=[0, 0.2], showticklabels=False)
fig['layout']['yaxis2'] = dict(domain=[0.2, 0.8])
rangeselector = dict(
    visibe = True,
    x = 0, y = 0.9,
    bgcolor = 'rgba(150, 200, 250, 0.4)',
    font = dict( size = 13 ),
    buttons=list([
        dict(count=1,
            label='1 day',
            step='day',
            stepmode='backward'),
        dict(count=7,
            label='7 days',
            step='day',
            stepmode='backward'),
        dict(count=15,
            label='15 days',
            step='day',
            stepmode='backward'),
        dict(count=1,
            label='1 mo',
            step='month',
            stepmode='backward'),
        dict(step='all')
    ]))
fig['layout']['xaxis']['rangeselector'] = rangeselector
fig['data'].append( dict( x=df['Date'], y=df['SMA'], type='scatter', mode='lines',
                         yaxis='y2', name='Moving Average' ) )

colors = []
for i in range(len(df['close'])):
    if i != 0:
        if df['close'][i] > df['close'][i-1]:
            colors.append(INCREASING_COLOR)
        else:
            colors.append(DECREASING_COLOR)
    else:
        colors.append(DECREASING_COLOR)

fig['data'].append(dict(x=df['Date'], y=df['volumeto'],
                         marker=dict( color=colors),
                         type='bar', yaxis='y', name='Volume'))

offline.plot(fig, filename='docs/dashboard_1.html', validate=False)

# plot 2 dashboard
DASH1 = ['analysis_page_views','charts_page_views','comments','fb_likes','fb_talking_about']
fig = tools.make_subplots(rows=5, cols=1, subplot_titles=DASH1)
trace = go.Scatter(x=df['Date'], y=df['analysis_page_views'].pct_change(), name='analysis_page_views pct_change', fill='tonexty', mode='none')
fig.append_trace(trace, 1, 1)
trace = go.Scatter(x=df['Date'], y=df['charts_page_views'].pct_change(), name='charts_page_views pct change', fill='tonexty', mode='none')
fig.append_trace(trace, 2, 1)
trace = go.Bar(x=df['Date'], y=df['comments'].pct_change(), name='comments pct change')
fig.append_trace(trace, 3, 1)
trace = go.Scatter(x=df['Date'], y=df['fb_likes'], name='fb_likes', fill='tonexty', mode='none')
fig.append_trace(trace, 4, 1)
trace = go.Scatter(x=df['Date'], y=df['fb_talking_about'], name='fb_talking_about', fill='tonexty', mode='none')
fig.append_trace(trace, 5, 1)
fig['layout'].update(title='Dashboard 2',
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929')
offline.plot(fig, filename='docs/dashboard_2.html')

# plot 3 dashboard
DASH2 = ['followers','forum_page_views', 'influence_page_views','markets_page_views','overview_page_views']
fig = tools.make_subplots(rows=5, cols=1, subplot_titles=DASH2)
trace = go.Bar(x=df['Date'], y=df['followers'].pct_change(), name='followers pct change')
fig.append_trace(trace, 1, 1)
trace = go.Scatter(x=df['Date'], y=df['forum_page_views'].pct_change(), name='forum_page_views pct change', fill='tonexty', mode='none')
fig.append_trace(trace, 2, 1)
trace = go.Scatter(x=df['Date'], y=df['influence_page_views'].pct_change(), name='influence_page_views pct change', fill='tonexty', mode='none')
fig.append_trace(trace, 3, 1)
trace = go.Scatter(x=df['Date'], y=df['markets_page_views'].pct_change(), name='markets_page_views pct change', fill='tonexty', mode='none')
fig.append_trace(trace, 4, 1)
trace = go.Scatter(x=df['Date'], y=df['overview_page_views'].pct_change(), name='overview_page_views pct change', fill='tonexty', mode='none')
fig.append_trace(trace, 5, 1)
fig['layout'].update(title='Dashboard 3',
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929')
offline.plot(fig, filename='docs/dashboard_3.html')