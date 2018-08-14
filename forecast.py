import sys
from termcolor import colored
if len(sys.argv) != 3:
	print(colored("Usage: python3 forecast.py [asset] [days]", 'red', attrs=['bold']))
	exit()
import pandas as pd
import matplotlib.pyplot as plt
import fbprophet, sys, configs.get_datasets
from configs.functions import print_dollar
from configs.vars import days, todays_month, todays_day, currency, changepoint_prior_scale
#------------------------------------------------------------->
asset_name, forecast_days = sys.argv[1], sys.argv[2]
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
df_prophet.plot(df_forecast, xlabel='Date', ylabel='Price')
# df_prophet.plot_components(df_forecast)
plt.title(asset_name.upper())
plt.ylabel('Price ({})'.format(currency.upper()))
print_dollar()
plt.show()
