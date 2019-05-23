"""Functions used to preprocess the timeseries

Lucas Draichi
2019
"""

import datetime
import talib
import os
import colorama
import requests
import pandas as pd
import numpy as np
from termcolor import colored
from configs.vars import DF_TRAIN_SIZE

colorama.init()

def get_datasets(symbol, to_symbol, histo, limit):
    """Fetch the API and precess the desired pair

    Arguments:
        symbol {str} -- First pair
        to_symbol {str} -- Second pair
        histo {str ['day', 'hour']} -- Granularity
        limit {int [100 - 2000]} -- [description]

    Returns:
        pandas.Dataframe -- The OHLCV and indicators dataframe
    """
    df_train_path = 'datasets/bot_train_{}_{}_{}.csv'.format(symbol + to_symbol, limit, histo)
    df_rollout_path = 'datasets/bot_rollout_{}_{}_{}.csv'.format(symbol + to_symbol, limit, histo)

    if not os.path.exists(df_train_path):
        headers = {'User-Agent': 'Mozilla/5.0', 'authorization': 'Apikey 3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'}

        # OHLC
        url = 'https://min-api.cryptocompare.com/data/histo{}?fsym={}&tsym={}&e=Binance&limit={}'.format(histo, symbol, to_symbol, limit)
        print(colored('> downloading ' + symbol + '/' + to_symbol + ' OHLCV', 'green'))
        response = requests.get(url, headers=headers)
        json_response = response.json()
        status = json_response['Response']
        if status == "Error":
            print(colored('=== {} ==='.format(json_response['Message']), 'red'))
            raise AssertionError()
        result = json_response['Data']
        df = pd.DataFrame(result)
        df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
        df.drop('time', axis=1, inplace=True)

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
        df.loc[:, 'ADX'] = talib.ADX(high, low, close, timeperiod=12)
        df.loc[:, 'ADXR'] = talib.ADXR(high, low, close, timeperiod=13)
        df.loc[:, 'APO'] = talib.APO(close, fastperiod=5, slowperiod=10, matype=0)
        df.loc[:, 'AROON_down'], df.loc[:, 'AROON_up'] = talib.AROON(high, low, timeperiod=15)
        df.loc[:, 'AROONOSC'] = talib.AROONOSC(high, low, timeperiod=13)
        df.loc[:, 'BOP'] = talib.BOP(open_price, high, low, close)
        df.loc[:, 'CCI'] = talib.CCI(high, low, close, timeperiod=13)
        df.loc[:, 'CMO'] = talib.CMO(close, timeperiod=14)
        df.loc[:, 'DX'] = talib.DX(high, low, close, timeperiod=10)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(close, fastperiod=5, slowperiod=10, signalperiod=20)
        df.loc[:, 'MFI'] = talib.MFI(high, low, close, volume, timeperiod=12)
        df.loc[:, 'MINUS_DI'] = talib.MINUS_DI(high, low, close, timeperiod=10)
        df.loc[:, 'MINUS_DM'] = talib.MINUS_DM(high, low, timeperiod=14)
        df.loc[:, 'MOM'] = talib.MOM(close, timeperiod=20)
        df.loc[:, 'PPO'] = talib.PPO(close, fastperiod=17, slowperiod=35, matype=2)
        df.loc[:, 'ROC'] = talib.ROC(close, timeperiod=12)
        df.loc[:, 'RSI'] = talib.RSI(close, timeperiod=25)
        df.loc[:, 'STOCH_k'], df.loc[:, 'STOCH_d'] = talib.STOCH(high, low, close, fastk_period=35, slowk_period=12, slowk_matype=0, slowd_period=7, slowd_matype=0)
        df.loc[:, 'STOCHF_k'], df.loc[:, 'STOCHF_d'] = talib.STOCHF(high, low, close, fastk_period=28, fastd_period=14, fastd_matype=0)
        df.loc[:, 'STOCHRSI_K'], df.loc[:, 'STOCHRSI_D'] = talib.STOCHRSI(close, timeperiod=35, fastk_period=12, fastd_period=10, fastd_matype=1)
        df.loc[:, 'TRIX'] = talib.TRIX(close, timeperiod=30)
        df.loc[:, 'ULTOSC'] = talib.ULTOSC(high, low, close, timeperiod1=14, timeperiod2=28, timeperiod3=35)
        df.loc[:, 'WILLR'] = talib.WILLR(high, low, close, timeperiod=35)
        # overlap studies
        df.loc[:, 'BBANDS_upper'], df.loc[:, 'BBANDS_middle'], df.loc[:, 'BBANDS_lower'] = talib.BBANDS(close, timeperiod=12, nbdevup=2, nbdevdn=2, matype=0)
        df.loc[:, 'DEMA'] = talib.DEMA(close, timeperiod=30)
        df.loc[:, 'EMA'] = talib.EMA(close, timeperiod=7)
        df.loc[:, 'HT_TRENDLINE'] = talib.HT_TRENDLINE(close)
        df.loc[:, 'KAMA'] = talib.KAMA(close, timeperiod=5)
        df.loc[:, 'MA'] = talib.MA(close, timeperiod=5, matype=0)
        df.loc[:, 'MIDPOINT'] = talib.MIDPOINT(close, timeperiod=20)
        df.loc[:, 'WMA'] = talib.WMA(close, timeperiod=15)
        df.loc[:, 'SMA'] = talib.SMA(close)
        # pattern recoginition
        df.loc[:, 'CDL2CROWS'] = talib.CDL2CROWS(open_price, high, low, close)
        df.loc[:, 'CDL3BLACKCROWS'] = talib.CDL3BLACKCROWS(open_price, high, low, close)
        df.loc[:, 'CDL3INSIDE'] = talib.CDL3INSIDE(open_price, high, low, close)
        df.loc[:, 'CDL3LINESTRIKE'] = talib.CDL3LINESTRIKE(open_price, high, low, close)
        # price transform
        df.loc[:, 'WCLPRICE'] = talib.WCLPRICE(high, low, close)
        # statistic funcitons
        df.loc[:, 'BETA'] = talib.BETA(high, low, timeperiod=20)
        df.loc[:, 'CORREL'] = talib.CORREL(high, low, timeperiod=20)
        df.loc[:, 'STDDEV'] = talib.STDDEV(close, timeperiod=20, nbdev=1)
        df.loc[:, 'TSF'] = talib.TSF(close, timeperiod=20)
        df.loc[:, 'VAR'] = talib.VAR(close, timeperiod=20, nbdev=1)
        # volatility indicators
        df.loc[:, 'ATR'] = talib.ATR(high, low, close, timeperiod=7)
        df.loc[:, 'NATR'] = talib.NATR(high, low, close, timeperiod=20)
        df.loc[:, 'TRANGE'] = talib.TRANGE(high, low, close)
        # volume indicators
        df.loc[:, 'AD'] = talib.AD(high, low, close, volume)
        df.loc[:, 'ADOSC'] = talib.ADOSC(high, low, close, volume, fastperiod=10, slowperiod=20)
        df.loc[:, 'OBV'] = talib.OBV(close, volume)

        # df.fillna(df.mean(), inplace=True)
        df.dropna(inplace=True)
        df.set_index('Date', inplace=True)
        train_size = round(len(df) * DF_TRAIN_SIZE) # 75% to train -> test with different value
        df_train = df[:train_size]
        df_rollout = df[train_size:]
        df_train.to_csv(df_train_path)
        df_rollout.to_csv(df_rollout_path)
        df_train = pd.read_csv(df_train_path) # re-read to avoid indexing issue w/ Ray
        df_rollout = pd.read_csv(df_rollout_path)
    else:
        print(colored('> feching ' + symbol + '/' + to_symbol + ' from cache OHLCV', 'magenta'))
        df_train = pd.read_csv(df_train_path)
        df_rollout = pd.read_csv(df_rollout_path)
        # df_train.set_index('Date', inplace=True)
        # df_rollout.set_index('Date', inplace=True)

    return df_train, df_rollout

#------------------------------------------------------------->

def print_dollar():
    print(chr(27) + "[2J")
    print(colored("""
||====================================================================||
||//$\\\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\//$\\\||
||(100)==================| FEDERAL RESERVE NOTE |================(100)||
||\\\$//        ~         '------========--------'                \\\$//||
||<< /        /$\              // ____ \\\                         \ >>||
||>>|  12    //L\\\            // ///..) \\\         L38036133B   12 |<<||
||<<|        \\\ //           || <||  >\  ||                        |>>||
||>>|         \$/            ||  $$ --/  ||        One Hundred     |<<||
||====================================================================||>||
||//$\\\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\//$\\\||<||
||(100)==================| FEDERAL RESERVE NOTE |================(100)||>||
||\\\$//        ~         '------========--------'                \\\$//||\||
||<< /        /$\              // ____ \\\                         \ >>||)||
||>>|  12    //L\\\            // ///..) \\\         L38036133B   12 |<<||/||
||<<|        \\\ //           || <||  >\  ||                        |>>||=||
||>>|         \$/            ||  $$ --/  ||        One Hundred     |<<||
||<<|      L38036133B        *\\\  |\_/  //* series                 |>>||
||>>|  12                     *\\\/___\_//*   1989                  |<<||
||<<\      Treasurer     ______/Franklin\________     Secretary 12 />>||
||//$\                 ~|UNITED STATES OF AMERICA|~               /$\\\||
||(100)===================  ONE HUNDRED DOLLARS =================(100)||
||\\\$//\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\\\$//||
||====================================================================||
    """, 'green', attrs=['bold']))