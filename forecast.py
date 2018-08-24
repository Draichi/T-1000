import sys
from termcolor import colored
if len(sys.argv) != 4:
	print(colored("Usage: python3 forecast.py [asset] [days] [changepoint_prior_scale]", 'red', attrs=['bold']))
	exit()
import pandas as pd
import matplotlib.pyplot as plt
import fbprophet, sys, configs.get_datasets
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
df_prophet.plot(df_forecast, xlabel='Date', ylabel='Price')
# df_prophet.plot_components(df_forecast)
plt.title('Forecasting {} days, {}, {} days data, {} changepoint prior scale'.format(forecast_days,asset_name.upper(),days,changepoint_prior_scale))
plt.ylabel('Price ({})'.format(currency.upper()))
print_dollar()
plt.show()
