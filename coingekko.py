import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go
import requests, datetime, get_datasets
import pandas as pd
from configs.vars import coins, days, todays_month, todays_day, keys

coin_data = {}
for coin in coins:
    data = pd.read_csv('datasets/{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days))
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
        name = str(coin).upper(),
    )
    data.append(trace)

layout = go.Layout(
    plot_bgcolor='#010008',
    paper_bgcolor='#010008',
    title='Altcoins Logarithmic Prices in {} Days'.format(days),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price (BTC)',
        type='log'
    )
)

offline.plot({'data': data, 'layout': layout})

