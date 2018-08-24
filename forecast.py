import sys
from termcolor import colored
if len(sys.argv) != 4:
	print(colored("Usage: python3 forecast.py [asset] [days] [changepoint_prior_scale]", 'red', attrs=['bold']))
	exit()
import pandas as pd
import matplotlib.pyplot as plt
import fbprophet, sys, configs.get_datasets
import plotly.offline as offline
import plotly.graph_objs as go
from configs.functions import print_dollar
from configs.vars import days, todays_month, todays_day, currency
#------------------------------------------------------------->
plt.rcParams.update({
    "lines.color": "#2d2929",
    "patch.edgecolor": "#2d2929",
    "text.color": "#e5e5e5",
    "axes.facecolor": "#2d2929",
    "axes.titlepad": 1.0,
    "axes.edgecolor": "#2d2929",
    "axes.labelcolor": "#e5e5e5",
    "xtick.color": "#e5e5e5",
    "ytick.color": "#e5e5e5",
    "grid.color": "#2d2929",
    "figure.facecolor": "#2d2929",
    "figure.edgecolor": "#2d2929",
    "savefig.facecolor": "#2d2929",
    "savefig.edgecolor": "#2d2929"}
)
#------------------------------------------------------------->
asset_name, forecast_days, changepoint_prior_scale = sys.argv[1], sys.argv[2], sys.argv[3]
df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day,todays_month,asset_name,days,currency))
df['ds'] = df['date']
df['y'] = df['prices']
df = df[['ds', 'y']]
#------------------------------------------------------------->
df_prophet = fbprophet.Prophet(changepoint_prior_scale=changepoint_prior_scale)
df_prophet.fit(df)
#------------------------------------------------------------->
df_forecast = df_prophet.make_future_dataframe(periods=int(forecast_days))
df_forecast = df_prophet.predict(df_forecast)
df_forecast.to_csv('datasets/{}-{}_{}_forecast_d{}_{}.csv'.format(todays_day,todays_month,asset_name,days,currency))
#------------------------------------------------------------->
# df_prophet.plot_components(df_forecast)
layout = go.Layout(
    plot_bgcolor='#2d2929',
    paper_bgcolor='#2d2929',
    title='{} price forecast, {} days data, changepoint prior scale: {}'.format(asset_name,days,changepoint_prior_scale).title(),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price ({})'.format(currency.upper())
    )
)
data = [
    go.Scatter(x=df['ds'], y=df['y'], name='PRICE', mode='markers',marker=dict(symbol='diamond-dot')),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='PRICE HAT'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_upper'], fill='tonexty', mode='none', name='UPPER HAT', fillcolor='rgba(204,231,230,.31)'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_lower'], fill='tonexty', mode='none', name='LOWER HAT', fillcolor='rgba(193,175,230,.31)'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['trend'], name='TREND')
]

offline.plot({'data': data, 'layout': layout})
print_dollar()
