import sys
from termcolor import colored
import colorama
colorama.init()
if len(sys.argv) != 2:
    print(colored("Usage: python3 scatter.py [layout_type]", 'red', attrs=['bold']))
    exit()
import plotly.offline as offline
import plotly.graph_objs as go
import configs.get_datasets
import pandas as pd
from configs.vars import coins, days, todays_month, todays_day, currency
#------------------------------------------------------------->
layout_type = sys.argv[1]
data = []
for coin in coins:
    df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, coin, days, currency))
    trace = go.Scatter(
        x=df.date,
        y=df['prices'],
        name = str(coin).upper(),
    )
    data.append(trace)
#------------------------------------------------------------->
layout = go.Layout(
    plot_bgcolor='#2d2929',
    paper_bgcolor='#2d2929',
    title='{} Prices in {} Days'.format(layout_type,days).title(),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price ({})'.format(currency.upper()),
        type=layout_type
    )
)
#------------------------------------------------------------->
offline.plot({'data': data, 'layout': layout})
