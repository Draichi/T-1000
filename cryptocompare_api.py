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

# TODO
# X fazer com que a database seja salva com todos os indicadores
# - organizar essas funçoes em uma classe
# - fazer com que o environment load essa database
# - copiar o step de algum bom trading env para o train_trading_bot.py
# - ter uma flag para exibir esses indicadores

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
if not (os.path.exists('datasets/ETH-BTC.csv')):
    cprint('> downloading', 'yellow', attrs=['bold'])
    headers = {'User-Agent': 'Mozilla/5.0', 'authorization': 'Apikey 3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'}

    # OHLC
    url = 'https://min-api.cryptocompare.com/data/histohour?fsym=ETH&tsym=BTC&e=Binance&limit=2000'
    response = requests.get(url, headers=headers)
    json_response = response.json()
    result = json_response['Data']
    # df = pd.DataFrame(result)
    df1 = pd.DataFrame(result)

    # social
    url = 'https://min-api.cryptocompare.com/data/social/coin/histo/hour?coinId=7605&limit=2000'
    response = requests.get(url, headers=headers)
    json_response = response.json()
    result = json_response['Data']
    df2 = pd.DataFrame(result)

    # #merge
    df = pd.merge(df1, df2, on='time')
    df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
    df.drop('time', axis=1, inplace=True)
    df.set_index('Date', inplace=True)

    # indicators
    # https://github.com/mrjbq7/ta-lib/blob/master/docs/func.md
    open_price, high, low, close = np.array(df['open']), np.array(df['high']), np.array(df['low']), np.array(df['close'])
    volume = np.array(df['volumefrom'])
    # cycle indicators
    df.loc[:, 'HT_DCPERIOD'] = talib.HT_DCPERIOD(close)
    df.loc[:, 'HT_DCPHASE'] = talib.HT_DCPHASE(close)
    df.loc[:, 'HT_PHASOR_inphase'], df.loc[:, 'HT_PHASOR_quadrature'] = talib.HT_PHASOR(close)
    df.loc[:, 'HT_SINE_sine'], df.loc[:, 'HT_SINE_leadsine'] = talib.HT_SINE(close)
    df.loc[:, 'HT_TRENDMODE'] = talib.HT_TRENDMODE(close)
    # momemtum indicators
    df.loc[:, 'ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df.loc[:, 'ADXR'] = talib.ADXR(high, low, close, timeperiod=14)
    df.loc[:, 'APO'] = talib.APO(close, fastperiod=12, slowperiod=26, matype=0)
    df.loc[:, 'AROON_down'], df.loc[:, 'AROON_up'] = talib.AROON(high, low, timeperiod=14)
    df.loc[:, 'AROONOSC'] = talib.AROONOSC(high, low, timeperiod=14)
    df.loc[:, 'BOP'] = talib.BOP(open_price, high, low, close)
    df.loc[:, 'CCI'] = talib.CCI(high, low, close, timeperiod=14)
    df.loc[:, 'CMO'] = talib.CMO(close, timeperiod=14)
    df.loc[:, 'DX'] = talib.DX(high, low, close, timeperiod=14)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df.loc[:, 'MFI'] = talib.MFI(high, low, close, volume, timeperiod=14)
    df.loc[:, 'MINUS_DI'] = talib.MINUS_DI(high, low, close, timeperiod=14)
    df.loc[:, 'MINUS_DM'] = talib.MINUS_DM(high, low, timeperiod=14)
    df.loc[:, 'MOM'] = talib.MOM(close, timeperiod=10)
    df.loc[:, 'PPO'] = talib.PPO(close, fastperiod=12, slowperiod=26, matype=0)
    df.loc[:, 'ROC'] = talib.ROC(close, timeperiod=10)
    df.loc[:, 'RSI'] = talib.RSI(close, timeperiod=14)
    df.loc[:, 'STOCH_k'], df.loc[:, 'STOCH_d'] = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    df.loc[:, 'STOCHF_k'], df.loc[:, 'STOCHF_d'] = talib.STOCHF(high, low, close, fastk_period=5, fastd_period=3, fastd_matype=0)
    df.loc[:, 'STOCHRSI_K'], df.loc[:, 'STOCHRSI_D'] = talib.STOCHRSI(close, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)
    df.loc[:, 'TRIX'] = talib.TRIX(close, timeperiod=30)
    df.loc[:, 'ULTOSC'] = talib.ULTOSC(high, low, close, timeperiod1=7, timeperiod2=14, timeperiod3=28)
    df.loc[:, 'WILLR'] = talib.WILLR(high, low, close, timeperiod=14)
    # overlap studies
    df.loc[:, 'BBANDS_upper'], df.loc[:, 'BBANDS_middle'], df.loc[:, 'BBANDS_lower'] = talib.BBANDS(close, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)
    df.loc[:, 'DEMA'] = talib.DEMA(close, timeperiod=30)
    df.loc[:, 'EMA'] = talib.EMA(close, timeperiod=30)
    df.loc[:, 'HT_TRENDLINE'] = talib.HT_TRENDLINE(close)
    df.loc[:, 'KAMA'] = talib.KAMA(close, timeperiod=30)
    df.loc[:, 'MA'] = talib.MA(close, timeperiod=30, matype=0)
    df.loc[:, 'MIDPOINT'] = talib.MIDPOINT(close, timeperiod=14)
    df.loc[:, 'WMA'] = talib.WMA(close, timeperiod=30)
    df.loc[:, 'SMA'] = talib.SMA(close)
    # pattern recoginition
    df.loc[:, 'CDL2CROWS'] = talib.CDL2CROWS(open_price, high, low, close)
    df.loc[:, 'CDL3BLACKCROWS'] = talib.CDL3BLACKCROWS(open_price, high, low, close)
    df.loc[:, 'CDL3INSIDE'] = talib.CDL3INSIDE(open_price, high, low, close)
    df.loc[:, 'CDL3LINESTRIKE'] = talib.CDL3LINESTRIKE(open_price, high, low, close)
    # price transform
    df.loc[:, 'WCLPRICE'] = talib.WCLPRICE(high, low, close)
    # statistic funcitons
    df.loc[:, 'BETA'] = talib.BETA(high, low, timeperiod=5)
    df.loc[:, 'CORREL'] = talib.CORREL(high, low, timeperiod=30)
    df.loc[:, 'STDDEV'] = talib.STDDEV(close, timeperiod=5, nbdev=1)
    df.loc[:, 'TSF'] = talib.TSF(close, timeperiod=14)
    df.loc[:, 'VAR'] = talib.VAR(close, timeperiod=5, nbdev=1)
    # volatility indicators
    df.loc[:, 'ATR'] = talib.ATR(high, low, close, timeperiod=14)
    df.loc[:, 'NATR'] = talib.NATR(high, low, close, timeperiod=14)
    df.loc[:, 'TRANGE'] = talib.TRANGE(high, low, close)
    # volume indicators
    df.loc[:, 'AD'] = talib.AD(high, low, close, volume)
    df.loc[:, 'ADOSC'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
    df.loc[:, 'OBV'] = talib.OBV(close, volume)

    df.fillna(df.mean(), inplace=True)
    df.to_csv('datasets/ETH-BTC.csv')
#------------------------------------------------------------->
else:
    cprint('> loading from cache')
    df = pd.read_csv('datasets/ETH-BTC.csv')
#------------------------------------------------------------->
quit()
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