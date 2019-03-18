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

            # renamed_columns = {field: title for field, title in ids, titles}
            # renamed_columns = {field: field.split('.')[-1] for field in ids}
            df.rename(index=str, columns=ids_and_titles, inplace=True)

            
            price_btc = np.array(df['Price BTC'])
            price_usd = np.array(df['Price $'])

            df.loc[:, 'SMA_USD'] = talib.SMA(price_usd)
            # df['SMA_USD'] = talib.SMA(price_usd)

            # df['MOM_USD'] = talib.MOM(price_usd, timeperiod=14)
            df.loc[:, 'MOM_USD'] = talib.MOM(price_usd, timeperiod=14)

            df.loc[:, 'CMO_USD'] = talib.CMO(price_usd, timeperiod=14)
            # df['CMO_USD'] = talib.CMO(price_usd, timeperiod=14)
            df['macd_USD'], df['macdsignal_USD'], df['macdhist_USD'] = talib.MACD(price_usd, fastperiod=12, slowperiod=26, signalperiod=9)
            df.to_csv('datasets/{}_{}_{}_{}.csv'.format(name, TIME_INTERVAL, FROM_DATE, TO_DATE))
            print(df.tail())
    #------------------------------------------------------------->        
    else:
        cprint('> loading {} from cache'.format(symbol.upper()), 'blue', attrs=['bold'])
#------------------------------------------------------------->
