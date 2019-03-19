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
        headers = {'User-Agent': 'Mozilla/5.0'}
        # fetch https://api.datalight.me/v1/object/ to get all objects.id
        objects_url = 'https://api.datalight.me/v1/object/'
        objects_response = requests.get(objects_url, headers=headers)
        objects_response_json = objects_response.json()
        ids = [object_id['id'] for object_id in objects_response_json['result']]
        ids_and_titles = {object_id['id']: object_id['title'] for object_id in objects_response_json['result']}
        str_ids = ','.join(ids)

        # now fetch the coin data
        url = 'https://api.datalight.me/v1/request/?coin='+STR_PORTFOLIO_SYMBOLS+'&fields='+str_ids+'&limit=10000&offset=0&order=date&time_interval='+TIME_INTERVAL+'&from_date='+FROM_DATE+'&to_date='+ TO_DATE
        response = requests.get(url, headers=headers)
        json_response = response.json()
        response_time = json_response['response_time']
        result = json_response['result']
        cprint("> fetched in {}".format(response_time), 'green', attrs=['bold'])

        # save the response in a df (its easier)
        df = pd.DataFrame(result)
        df['Date'] = pd.to_datetime(df['processed_date'], utc=True, unit='s')
        df.set_index('Date', inplace=True)
        df.drop('processed_date', axis=1, inplace=True)

        # now process the coins data
        dfs = [df.loc[df['Coin'] == coin.upper()] for coin in PORTFOLIO_SYMBOLS]
        for df in dfs:
            name = df['Coin'][0]
            # drop the null columns (only happen on altcoins)
            not_null_cols = [col for col in df.columns if df.loc[:, col].notna().any()]
            df = df[not_null_cols]

            df.rename(index=str, columns=ids_and_titles, inplace=True)
            df.drop(labels=['Total Supply','Max Supply', 'Rank', 'Available Supply', 'Website visits mo.'], axis=1, inplace=True)            
            # df.drop(labels=['Max Supply', 'Rank', 'ATH Volume $', 'Available Supply', 'ATH Marketcap $', 'ATL Marketcap $','ATH Price $', 'ATL Price $', 'Website visits mo.'], axis=1, inplace=True)            
            
            price_btc = np.array(df['Price BTC'])
            price_usd = np.array(df['Price $'])

            df.loc[:, 'SMA_USD'] = talib.SMA(price_usd)
            df.loc[:, 'SMA_BTC'] = talib.SMA(price_btc)
            df.loc[:, 'MOM_USD'] = talib.MOM(price_usd, timeperiod=14)
            df.loc[:, 'MOM_BTC'] = talib.MOM(price_btc, timeperiod=14)
            df.loc[:, 'CMO_USD'] = talib.CMO(price_usd, timeperiod=14)
            df.loc[:, 'CMO_BTC'] = talib.CMO(price_btc, timeperiod=14)
            df.loc[:, 'PPO_USD'] = talib.PPO(price_usd, fastperiod=12, slowperiod=26, matype=0)
            df.loc[:, 'PPO_BTC'] = talib.PPO(price_btc, fastperiod=12, slowperiod=26, matype=0)
            df.loc[:, 'ROC_USD'] = talib.ROC(price_usd, timeperiod=10)
            df.loc[:, 'ROC_BTC'] = talib.ROC(price_btc, timeperiod=10)
            df.loc[:, 'RSI_USD'] = talib.RSI(price_usd, timeperiod=14)
            df.loc[:, 'RSI_BTC'] = talib.RSI(price_btc, timeperiod=14)
            df.loc[:, 'STOCHRSI_USD_K'], df.loc[:, 'STOCHRSI_USD_D'] = talib.STOCHRSI(price_usd, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)
            df.loc[:, 'STOCHRSI_BTC_K'], df.loc[:, 'STOCHRSI_BTC_D'] = talib.STOCHRSI(price_btc, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)
            df['macd_USD'], df['macdsignal_USD'], df['macdhist_USD'] = talib.MACD(price_usd, fastperiod=12, slowperiod=26, signalperiod=9)
            df['macd_BTC'], df['macdsignal_BTC'], df['macdhist_BTC'] = talib.MACD(price_btc, fastperiod=12, slowperiod=26, signalperiod=9)
            df.fillna(df.mean(), inplace=True)
            df.to_csv('datasets/{}_{}_{}_{}.csv'.format(name, TIME_INTERVAL, FROM_DATE, TO_DATE))
    #------------------------------------------------------------->        
    else:
        cprint('> loading {} from cache'.format(symbol.upper()), 'blue', attrs=['bold'])
#------------------------------------------------------------->
