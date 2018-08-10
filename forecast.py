import pandas as pd
import matplotlib.pyplot as plt
import plotly.offline as offline
import plotly.graph_objs as go
import fbprophet, sys, get_datasets
from configs.vars import days, todays_month, todays_day, currency

if len(sys.argv) != 2:
	print(colored("Usage: python3 forecast.py [asset]", 'red', attrs=['bold']))
	exit()

asset_name = sys.argv[1]

# plt.style.use('dark_background')
df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, asset_name, days, currency))

# df.head(5)
df['ds'] = df['date']
df['y'] = df['prices']

df = df[['ds', 'y']]

df_prophet = fbprophet.Prophet(changepoint_prior_scale=0.35)
df_prophet.fit(df)

df_forecast = df_prophet.make_future_dataframe(periods=5)
df_forecast = df_prophet.predict(df_forecast)
df_forecast.to_csv('datasets/{}-{}_{}_forecast_d{}_{}.csv'.format(todays_day, todays_month, asset_name, days, currency))

df_prophet.plot(df_forecast, xlabel='Date', ylabel='Price')
# df_prophet.plot_components(df_forecast)
plt.title('Dash')

# plt.plot(dash.index, dash['y'])
# plt.title('Dash Price')
plt.ylabel('Price (BTC)')

# dash_trends['Semana'] = pd.to_datetime(dash_trends['Semana'])
# dash_changepoints = [str(date) for date in dash_prophet.changepoints]

# plt.plot(dash_trends['Semana'], dash_trends['Dash'], label = 'Dash')
# plt.vlines(dash_changepoints, ymin = 0, ymax= 100, colors = 'r', linewidth=0.6, linestyles = 'dashed', label = 'Changepoints')

# plt.grid('off')
# plt.ylabel('Relative Search Freq')
# plt.legend()
# plt.title('Tesla Search Terms and Changepoints')

plt.show()
# plt.plot(tesla.index, tesla['Adj. Close'], 'r')
# plt.title('Tesla Stock Price')
# plt.ylabel('Price ($)')
# plt.show()
# -------------
# fig = plt.figure(facecolor='green')
# ax = fig.add_subplot(111)
# ax.plot(dash['dash'], label='True Data')
# plt.show()
# --------------
