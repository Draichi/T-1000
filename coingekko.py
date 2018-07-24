import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go
import requests, datetime
import pandas as pd

# https://plot.ly/python/time-series/

coins = ['giant', 'rupaya', 'hush', 'fantasy-gold', 'ethereum']
keys = ['prices']
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day

def get_coin_data(coin):
    try:
        df = pd.read_csv('{}-{}-{}.csv'.format(coin, todays_day, todays_month))
        print('--- loading {} from cache'.format(coin))
    except (OSError, IOError) as e:
        print('--- downloading {}, this will take some while'.format(coin))
        url = 'https://api.coingecko.com/api/v3/coins/{}/market_chart?vs_currency=btc&days=1'.format(coin)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        df = pd.DataFrame(response.json())
        df.to_csv('{}-{}-{}.csv'.format(coin, todays_day, todays_month), index=False)
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
            data.loc[i, key] = price
    coin_data[coin] = data
    df = pd.DataFrame(coin_data[coin])
    df.to_csv('df_{}-{}-{}.csv'.format(coin, todays_day, todays_month), index=False)

data = []
for coin in coins:
    df = pd.read_csv('df_{}-{}-{}.csv'.format(coin, todays_day, todays_month))
    trace = go.Scatter(
        x=df['date'],
        y=df['prices'],
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

