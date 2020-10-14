import emoji
import random
from termcolor import colored

import datetime
import talib
import os
import colorama
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from yaspin import yaspin
from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.styles import Style

# build a basic prompt_toolkit style for styling the HTML wrapped text
style = Style.from_dict({
    'msg': '#4caf50 bold',
    'sub-msg': '#616161 italic',
    'loading': '#c9c344 italic'
})

colorama.init()


def loading():
    emojis = [':moneybag:', ':yen:', ':dollar:', ':pound:', ':euro:']
    chosed_emoji = emoji.emojize(random.choice(emojis), use_aliases=True)
    string = u'<b>> {}</b> <loading>loading...</loading>'.format(chosed_emoji)
    print_formatted_text(HTML(string), style=style)


class GenerateDatasets:
    def __init__(self,
                 asset,
                 currency,
                 granularity,
                 datapoints,
                 exchange,
                 df_train_size=0.75):
        load_dotenv()
        self.api_key = os.getenv('CRYPTOCOMPARE_API_KEY')
        if not self.api_key:
            raise EnvironmentError('CRYPTOCOMPARE_API_KEY not found on .env')
        self.df_train_size = df_train_size
        self.df_train_path = 'data/bot_train_{}_{}_{}.csv'.format(
            asset + currency, datapoints, granularity)
        self.df_rollout_path = 'data/bot_rollout_{}_{}_{}.csv'.format(
            asset + currency, datapoints, granularity)
        if not os.path.exists(self.df_rollout_path):
            self.df_train, self.df_rollout = self.fetch_data_from_server(asset,
                                                                         currency,
                                                                         granularity,
                                                                         datapoints,
                                                                         exchange)
        else:
            self.df_train, self.df_rollout = self.load_cashed_data(asset,
                                                                   currency)

    def fetch_data_from_server(self,
                               asset,
                               currency,
                               granularity,
                               datapoints,
                               exchange):
        headers = {'User-Agent': 'Mozilla/5.0',
                   'authorization': 'Apikey {}'.format(self.api_key)}
        url = ('https://min-api.cryptocompare.com/data/histo{}'
               '?fsym={}'
               '&tsym={}'
               '&limit={}'
               '&e={}'
               .format(granularity, asset, currency, datapoints, exchange))
        with yaspin(text='Downloading datasets') as sp:

            response = requests.get(url, headers=headers)
            sp.hide()
            string = (u'<b>></b>'
                       '<msg>{}/{}</msg>'
                       '<sub-msg>download complete</sub-msg>'
                       .format(asset, currency))
            print_formatted_text(HTML(string), style=style)
            sp.show()

        json_response = response.json()
        status = json_response['Response']
        if status == "Error":
            raise AssertionError(colored(json_response['Message'], 'red'))
        result = json_response['Data']
        df = pd.DataFrame(result)

        df_train, df_rollout = self.prepare_df_data(df)
        return df_train, df_rollout

    def prepare_df_data(self, df):
        df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
        df.drop('time', axis=1, inplace=True)

        # indicators
        # https://github.com/mrjbq7/ta-lib/blob/master/docs/func.md
        open_price, high, low, close = np.array(df['open']), np.array(
            df['high']), np.array(df['low']), np.array(df['close'])
        volume = np.array(df['volumefrom'], dtype=float)
        # cycle indicators
        df.loc[:, 'HT_DCPERIOD'] = talib.HT_DCPERIOD(close)
        df.loc[:, 'HT_DCPHASE'] = talib.HT_DCPHASE(close)
        HT_PHASOR_inphase, HT_PHASOR_quadrature = talib.HT_PHASOR(close)
        HT_SINE_sine, HT_SINE_leadsine = talib.HT_SINE(close)
        df.loc[:, 'HT_PHASOR_inphase'] = HT_PHASOR_inphase
        df.loc[:, 'HT_PHASOR_quadrature'] = HT_PHASOR_quadrature
        df.loc[:, 'HT_SINE_sine'] = HT_SINE_sine
        df.loc[:, 'HT_SINE_leadsine'] = HT_SINE_leadsine
        df.loc[:, 'HT_TRENDMODE'] = talib.HT_TRENDMODE(close)
        # momemtum indicators
        ADX_TIMEPERIOD = 12
        ADXR_TIMEPERIOD = 12
        APO_FAST, APO_SLOW, APO_MA_TYPE = 5, 10, 1
        AROON_TIMEPERIOD = 15
        AROONOSC_TIMEPERIOD = 13
        CCI_TIMEPERIOD = 13
        CMO_TIMEPERIOD = 14
        DX_TIMEPERIOD = 10
        df.loc[:, 'ADX'] = talib.ADX(high, low, close, ADX_TIMEPERIOD)
        df.loc[:, 'ADXR'] = talib.ADXR(high, low, close, ADXR_TIMEPERIOD)
        df.loc[:, 'APO'] = talib.APO(close, APO_FAST, APO_SLOW, APO_MA_TYPE)
        AROON_down, AROON_up = talib.AROON(high, low, AROON_TIMEPERIOD)
        df.loc[:, 'AROON_down'], df.loc[:, 'AROON_up'] = AROON_down, AROON_up
        df.loc[:, 'AROONOSC'] = talib.AROONOSC(high, low, AROONOSC_TIMEPERIOD)
        df.loc[:, 'BOP'] = talib.BOP(open_price, high, low, close)
        df.loc[:, 'CCI'] = talib.CCI(high, low, close, CCI_TIMEPERIOD)
        df.loc[:, 'CMO'] = talib.CMO(close, CMO_TIMEPERIOD)
        df.loc[:, 'DX'] = talib.DX(high, low, close, DX_TIMEPERIOD)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(close,
                                                                    fastperiod=5,
                                                                    slowperiod=10,
                                                                    signalperiod=20)
        df.loc[:, 'MFI'] = talib.MFI(high, low, close, volume, timeperiod=12)
        df.loc[:, 'MINUS_DI'] = talib.MINUS_DI(high, low, close, timeperiod=10)
        df.loc[:, 'MINUS_DM'] = talib.MINUS_DM(high, low, timeperiod=14)
        df.loc[:, 'MOM'] = talib.MOM(close, timeperiod=20)
        df.loc[:, 'PPO'] = talib.PPO(close,
                                     fastperiod=17,
                                     slowperiod=35,
                                     matype=2)
        df.loc[:, 'ROC'] = talib.ROC(close, timeperiod=12)
        df.loc[:, 'RSI'] = talib.RSI(close, timeperiod=25)
        df.loc[:, 'STOCH_k'], df.loc[:, 'STOCH_d'] = talib.STOCH(high,
                                                                 low,
                                                                 close,
                                                                 fastk_period=35,
                                                                 slowk_period=12,
                                                                 slowk_matype=0,
                                                                 slowd_period=7,
                                                                 slowd_matype=0)
        df.loc[:, 'STOCHF_k'], df.loc[:, 'STOCHF_d'] = talib.STOCHF(high,
                                                                    low,
                                                                    close,
                                                                    fastk_period=28,
                                                                    fastd_period=14,
                                                                    fastd_matype=0)
        df.loc[:, 'STOCHRSI_K'], df.loc[:, 'STOCHRSI_D'] = talib.STOCHRSI(close,
                                                                          timeperiod=35,
                                                                          fastk_period=12,
                                                                          fastd_period=10,
                                                                          fastd_matype=1)
        df.loc[:, 'TRIX'] = talib.TRIX(close, timeperiod=30)
        df.loc[:, 'ULTOSC'] = talib.ULTOSC(
            high, low, close, timeperiod1=14, timeperiod2=28, timeperiod3=35)
        df.loc[:, 'WILLR'] = talib.WILLR(high, low, close, timeperiod=35)
        # overlap studies
        df.loc[:, 'BBANDS_upper'], df.loc[:, 'BBANDS_middle'], df.loc[:, 'BBANDS_lower'] = talib.BBANDS(
            close, timeperiod=12, nbdevup=2, nbdevdn=2, matype=0)
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
        df.loc[:, 'CDL3BLACKCROWS'] = talib.CDL3BLACKCROWS(
            open_price, high, low, close)
        df.loc[:, 'CDL3INSIDE'] = talib.CDL3INSIDE(
            open_price, high, low, close)
        df.loc[:, 'CDL3LINESTRIKE'] = talib.CDL3LINESTRIKE(
            open_price, high, low, close)
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
        df.loc[:, 'ADOSC'] = talib.ADOSC(
            high, low, close, volume, fastperiod=10, slowperiod=20)
        df.loc[:, 'OBV'] = talib.OBV(close, volume)

        # df.fillna(df.mean(), inplace=True)
        df.dropna(inplace=True)
        df.set_index('Date', inplace=True)
        # print(colored('> caching' + asset + '/' + currency + ':)', 'cyan'))
        # 75% to train -> test with different value
        train_size = round(len(df) * self.df_train_size)
        df_train = df[:train_size]
        df_rollout = df[train_size:]
        df_train.to_csv(self.df_train_path)
        df_rollout.to_csv(self.df_rollout_path)
        # re-read to avoid indexing issue w/ Ray
        df_train = pd.read_csv(self.df_train_path)
        df_rollout = pd.read_csv(self.df_rollout_path)
        return df_train, df_rollout

    def load_cashed_data(self, asset, currency):
        print_formatted_text(HTML(
            u'<b>></b> <msg>{}/{}</msg> <sub-msg>cached</sub-msg>'.format(
                asset, currency)
        ), style=style)

        # print(colored('> feching ' + asset + '/' + currency + ' from cache :)', 'magenta'))
        df_train = pd.read_csv(df_train_path)
        df_rollout = pd.read_csv(df_rollout_path)
        return df_train, df_rollout
