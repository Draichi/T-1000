# pip3 install fbprophet
import pandas as pd
import matplotlib.pyplot as plt
import plotly.offline as offline
import plotly.graph_objs as go
import fbprophet
# plt.style.use('dark_background')
dash = pd.read_csv('datasets/df_binancecoin-6-8_400-days.csv')
# dash_trends = pd.read_csv('dash_trends.csv')

dash.head(5)
dash['ds'] = dash['date']
dash['y'] = dash['binancecoin']

dash = dash[['ds', 'y']]

dash_prophet = fbprophet.Prophet(changepoint_prior_scale=0.35)
dash_prophet.fit(dash)

dash_forecast = dash_prophet.make_future_dataframe(periods=30)
dash_forecast = dash_prophet.predict(dash_forecast)

dash_prophet.plot(dash_forecast, xlabel='Date', ylabel='Price')
dash_prophet.plot_components(dash_forecast)
# plt.title('Dash')

# plt.plot(dash.index, dash['y'])
# plt.title('Dash Price')
# plt.ylabel('Price (BTC)')

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
# def plot_results_multiple(predicted_data, true_data, prediction_len):
#     fig = plt.figure(facecolor='white')
#     ax = fig.add_subplot(111)
#     ax.plot(true_data, label='True Data')
#     #Pad the list of predictions to shift it in the graph to it's correct start
#     for i, data in enumerate(predicted_data):
#         padding = [None for p in range(i * prediction_len)]
#         plt.plot(padding + data, label='Prediction')
#         plt.legend()
#     plt.show()

# data = go.Scatter(
#     x=dash.date,
#     y=dash['dash'],
#     hoverinfo='y',
#     name = 'Dash',
# )
# layout = go.Layout(
#     plot_bgcolor='#010008',
#     paper_bgcolor='#010008',
#     title='Dash',
#     font=dict(color='rgb(255, 255, 255)'),
#     legend=dict(orientation="h"),
#     xaxis=dict(type='date'),
#     yaxis=dict(
#         title='Price (BTC)',
#         type='log'
#     )
# )
# #------------------------------------------------------------->
# offline.plot({'data': [data], 'layout': layout})
