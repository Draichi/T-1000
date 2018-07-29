import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go
import requests, datetime
import pandas as pd
from configs.vars import coins, days, todays_month, todays_day, keys

# https://plot.ly/python/time-series/

# coins = ['giant','rupaya','zcoin','nano','ethereum','steem']
# coins = ['dash','zcoin','steem','bitshares','nano','bitcoin-cash','ethereum-classic','ethereum','bitcoin','litecoin','monero']

def get_coin_data(coin):
    try:
        df = pd.read_csv('datasets/{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days))
        print('--- loading {} from cache'.format(coin))
    except (OSError, IOError) as e:
        print('--- downloading {}, this will take some while'.format(coin))
        url = 'https://api.coingecko.com/api/v3/coins/{}/market_chart?vs_currency=btc&days={}'.format(coin, days)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        df = pd.DataFrame(response.json())
        df.to_csv('datasets/{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days), index=False)
        print('--- caching {}'.format(coin))
    return df

coin_data = {}
for coin in coins:
    data = get_coin_data(coin)
    for key in keys:
        for i, item in enumerate(data[key]):
            str_item = str(item)
            current_item = str_item.replace('[', '').replace(']', '').split(',')
            date = current_item[0]
            price = current_item[1]
            dt = datetime.datetime.fromtimestamp(int(date)/1000).strftime('%Y-%m-%d %H:%M:%S')
            data.loc[i, 'date'] = dt
            data.loc[i, coin] = price
    data = data[['date', coin]]
    data.set_index('date', inplace=True)
    df = pd.DataFrame(data)
    df.to_csv('datasets/df_{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days))

data = []
for coin in coins:
    df = pd.read_csv('datasets/df_{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days))
    trace = go.Scatter(
        x=df.date,
        y=df[coin],
        hoverinfo='y',
        name = coin,
    )
    data.append(trace)

layout = go.Layout(
    plot_bgcolor='#010008',
    paper_bgcolor='#010008',
    yaxis=dict(
        type='log'
    )
)

offline.plot({'data': data, 'layout': layout})

