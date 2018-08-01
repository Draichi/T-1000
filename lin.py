import plotly.offline as offline
import plotly.graph_objs as go
import get_datasets
import pandas as pd
from configs.vars import coins, days, todays_month, todays_day
#------------------------------------------------------------->
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
#------------------------------------------------------------->
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
#------------------------------------------------------------->
offline.plot({'data': data, 'layout': layout})
