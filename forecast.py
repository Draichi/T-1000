import sys
from termcolor import colored
import colorama
colorama.init()
if len(sys.argv) != 4:
	print(colored("Usage: python3 forecast.py [asset] [days] [changepoint_prior_scale]", 'red', attrs=['bold']))
	exit()
import pandas as pd
import fbprophet, sys, configs.get_datasets
import plotly.offline as offline
import plotly.graph_objs as go
from configs.functions import print_dollar
from configs.vars import days, todays_month, todays_day, currency
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
    title='{} price forecast, changepoint prior scale: {}'.format(asset_name,changepoint_prior_scale).title(),
    font=dict(color='rgb(255, 255, 255)'),
    legend=dict(orientation="h"),
    xaxis=dict(type='date'),
    yaxis=dict(
        title='Price ({})'.format(currency.upper())
    )
)
data = [
    go.Scatter(x=df['ds'], y=df['y'], name='Price', line=dict(color='#94B7F5')),
    # go.Scatter(x=df['ds'], y=df['y'], name='Price', mode='markers',marker=dict(symbol='y-up-open',color='#e5e5e5')),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='Price Hat'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_upper'], fill='tonexty', mode='none', name='Upper Hat', fillcolor='rgba(0,201,253,.21)'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_lower'], fill='tonexty', mode='none', name='Lower Hat', fillcolor='rgba(252,201,5,.05)'),
    go.Scatter(x=df_forecast['ds'], y=df_forecast['trend'], name='Trend')
]
offline.plot({'data': data, 'layout': layout})
print_dollar()
