import os
import pandas as pd
import requests
import datetime
from dotenv import load_dotenv

PATH_TO_COMPLETE_DATA_FRAME = 't1000/data/{}-{}-{}.csv'

def get_day_month_year():
    now = datetime.datetime.now()
    day = now.day
    month = now.month
    year = now.year
    return day, month, year


def get_data_frame():
    load_dotenv()
    CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY')

    if not CRYPTOCOMPARE_API_KEY:
        raise ImportError('CRYPTOCOMPARE_API_KEY not found on .env')
    
    day, month, year = get_day_month_year()
    
    complete_df_path = f't1000/data/{day}-{month}-{year}.csv'

    if os.path.exists(complete_df_path):
        print('> Fetching data_frame from cache')
        return pd.read_csv(complete_df_path)
    
    headers = {'User-Agent': 'Mozilla/5.0',
                   'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'}
    url = 'https://min-api.cryptocompare.com/data/histoday?fsym=BTC&tsym=USD&limit=150&'
    response = requests.get(url, headers=headers)
    json_response = response.json()
    status = json_response['Response']

    if status == "Error":
        print('Error fetching data_frame')
        raise AssertionError(json_response['Message'])

    result = json_response['Data']

    pandas_data_frame = pd.DataFrame(result)
    to_datetime_arg = pandas_data_frame['time']
    pandas_data_frame.drop(['time', 'conversionType',
                            'conversionSymbol'], axis=1, inplace=True)

    pandas_data_frame['Date'] = pd.to_datetime(
        arg=to_datetime_arg, utc=True, unit='s')
    pandas_data_frame.set_index('Date', inplace=True)

    pandas_data_frame.to_csv(complete_df_path)

    return pandas_data_frame
