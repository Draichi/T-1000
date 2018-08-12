import pandas as pd
import matplotlib.pyplot as plt
import plotly.offline as offline
import plotly.graph_objs as go
import fbprophet, sys, get_datasets
from termcolor import colored
from functions import print_dollar
from configs.vars import days, todays_month, todays_day, currency, changepoint_prior_scale

if len(sys.argv) != 3:
	print(colored("Usage: python3 forecast.py [asset] [days]", 'red', attrs=['bold']))
	exit()

asset_name, forecast_days = sys.argv[1], sys.argv[2]

# plt.style.use('dark_background')
df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, asset_name, days, currency))

# df.head(5)
df['ds'] = df['date']
df['y'] = df['prices']

df = df[['ds', 'y']]

df_prophet = fbprophet.Prophet(changepoint_prior_scale=changepoint_prior_scale)
df_prophet.fit(df)

df_forecast = df_prophet.make_future_dataframe(periods=int(forecast_days))
df_forecast = df_prophet.predict(df_forecast)
df_forecast.to_csv('datasets/{}-{}_{}_forecast_d{}_{}.csv'.format(todays_day, todays_month, asset_name, days, currency))

df_prophet.plot(df_forecast, xlabel='Date', ylabel='Price')
# df_prophet.plot_components(df_forecast)
plt.title(asset_name.upper())
plt.ylabel('Price ({})'.format(currency.upper()))
print_dollar()
plt.show()
