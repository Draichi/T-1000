import plotly.offline as offline
import plotly.graph_objs as go
import get_datasets
import pandas as pd
from configs.vars import coins, days, todays_month, todays_day, currency
#------------------------------------------------------------->
data = []
for coin in coins:
    df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, coin, days, currency))
    trace = go.Scatter(
        x=df.date,
        y=df['prices'],
        hoverinfo='y',
        name = str(coin).upper(),
    )
    data.append(trace)
#------------------------------------------------------------->
layout = go.Layout(
    plot_bgcolor='#010008',
    paper_bgcolor='#010008',
    title='Logarithm Prices in {} Days ({})'.format(days, currency.upper()),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price ({})'.format(currency.upper()),
        type='log'
    )
)
#------------------------------------------------------------->
offline.plot({'data': data, 'layout': layout})
