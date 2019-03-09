import pandas as pd
import numpy as np
from configs.vars import coins, days, todays_day, todays_month, currency
import plotly.graph_objs as go
import plotly.offline as offline
import matplotlib as plt



data = []
for coin in coins:
    df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, coin, days, currency))
    trace = go.Scatter(
        x=df.date,
        y=df['prices'].pct_change(),
        name = str(coin).upper(),
    )
    data.append(trace)
#------------------------------------------------------------->
layout = go.Layout(
    plot_bgcolor='#2d2929',
    paper_bgcolor='#2d2929',
    title='Prices in {} Days'.format(days).title(),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price ({})'.format(currency.upper())
    )
)
#------------------------------------------------------------->
offline.plot({'data': data, 'layout': layout})
