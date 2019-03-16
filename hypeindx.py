import pandas as pd
import talib
import numpy as np
import requests
import os
import colorama
from configs.vars import *
from termcolor import cprint
colorama.init()
#------------------------------------------------------------->

for symbol in PORTFOLIO_SYMBOLS:
    if not (os.path.exists('datasets/{}_{}_{}_{}.csv'.format(symbol.upper(), TIME_INTERVAL, FROM_DATE, TO_DATE))):
        cprint('> downloading', 'yellow', attrs=['bold'])
        url = 'https://api.datalight.me/v1/request/?coin='+STR_PORTFOLIO_SYMBOLS+'&fields='+STR_FIELDS+'&limit=10000&offset=0&order=date&time_interval='+TIME_INTERVAL+'&from_date='+FROM_DATE+'&to_date='+ TO_DATE
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        json_response = response.json()
        response_time = json_response['response_time']
        result = json_response['result']

        df = pd.DataFrame(result)
        df['Date'] = pd.to_datetime(df['processed_date'], utc=True, unit='s')
        df.set_index('Date', inplace=True)
        df.drop('processed_date', axis=1, inplace=True)
        dfs = [df.loc[df['Coin'] == coin.upper()] for coin in PORTFOLIO_SYMBOLS]
        for df in dfs:
            name = df['Coin'][0]
            price_btc = np.array(df['coinmarketcap.coin_btc.price_btc'])
            price_usd = np.array(df['coinmarketcap.coin.price_usd'])
            df['SMA_USD'] = talib.SMA(price_usd)
            df['MOM_USD'] = talib.MOM(price_usd, timeperiod=14)
            df['CMO_USD'] = talib.CMO(price_usd, timeperiod=14)
            df['macd_USD'], df['macdsignal_USD'], df['macdhist_USD'] = talib.MACD(price_usd, fastperiod=12, slowperiod=26, signalperiod=9)
            df.to_csv('datasets/{}_{}_{}_{}.csv'.format(name, TIME_INTERVAL, FROM_DATE, TO_DATE))
    #------------------------------------------------------------->        
        cprint("> fetched in {}".format(response_time), 'green', attrs=['bold'])
    else:
        cprint('> loading {} from cache'.format(symbol.upper()), 'blue', attrs=['bold'])
#------------------------------------------------------------->







# def get_df(asset_name):
#     asset = '{}-{}_{}_{}_{}.csv'.format(todays_day, todays_month, asset_name, days, currency)	
#     df = pd.read_csv('datasets/' + asset)
#     df.rename(index=str, columns={'prices': 'close'}, inplace=True)
#     close = np.array(df['close'])
#     df['open'] = df['close'].shift(1)
#     df['price_change'] = df['close'].pct_change()
#     df['SMA'] = talib.SMA(close)
#     df['MOM'] = talib.MOM(close, timeperiod=14)
#     df['CMO'] = talib.CMO(close, timeperiod=14)
#     df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
#     df['SMA50'] = df['close'].rolling(50).mean()
#     df['SMA20'] = df['close'].rolling(20).mean()
#     df['volume_x10e-7'] = df['total_volumes']*0.0000001
#     df['mark_cap_x10e-7'] = df['market_caps']*0.0000001
#     df.dropna(inplace=True)
#     df.drop(['total_volumes', 'market_caps'], inplace=True, axis=1)
#     df.set_index('date', inplace=True)
#     print(df.iloc[0])
#     return df

# get_df('ethereum')