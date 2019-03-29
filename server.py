import pandas as pd
import json, matplotlib, fbprophet, os
from flask import Flask, jsonify, request
from flask_cors import CORS
import gzip
from io import StringIO
from urllib.parse import urlparse

import plotly.graph_objs as go
import plotly.offline as offline

app = Flask(__name__)
CORS(app)

@app.route('/prophet', methods = ['POST'])
def prophet():
    values = request.get_json()
    # print(values)
    # return
    dataset = values.get('dataset')
    ds = dataset['ds']
    y = dataset['y']
    # print(ds)
    # print(y)
    changepoint_prior_scale = values.get('changepoint_prior_scale')
    forecast_days = values.get('forecast_days')
    df = pd.DataFrame(dataset)
    #------------------------------------------------------------->
    df_prophet = fbprophet.Prophet(changepoint_prior_scale=changepoint_prior_scale)
    df_prophet.fit(df)
    #------------------------------------------------------------->
    df_forecast = df_prophet.make_future_dataframe(periods=int(forecast_days))
    df_forecast = df_prophet.predict(df_forecast)
    df_forecast.to_json(orient='columns')
    # print(df_forecast.keys())
    layout = go.Layout(plot_bgcolor='#2d2929',
                       paper_bgcolor='#2d2929',
                       title='title',
                       font=dict(color='rgb(255, 255, 255)', size=17),
                       legend=dict(orientation="h"),
                       yaxis=dict(title='y_axis_title'))
    y = go.Scatter(x=df['ds'],
                    y=df['y'],
                    name='y',
                    line=dict(color='#94B7F5'))
    yhat = go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='yhat')
    yhat_upper = go.Scatter(x=df_forecast['ds'],
                    y=df_forecast['yhat_upper'],
                    fill='tonexty',
                    mode='none',
                    name='yhat_upper',
                    fillcolor='rgba(0,201,253,.21)')
    yhat_lower = go.Scatter(x=df_forecast['ds'],
                    y=df_forecast['yhat_lower'],
                    fill='tonexty',
                    mode='none',
                    name='yhat_lower',
                    fillcolor='rgba(252,201,5,.05)')
    offline.plot({'data': [y, yhat, yhat_lower, yhat_upper],
                 'layout': layout},
                 filename='docs/testeee.html')
    # seasonal = go.Scatter(x=df_forecast['ds'],
    #                 y=df_forecast['seasonal'],
    #                 fill='tonexty',
    #                 mode='none',
    #                 name='seasonal',
    #                 fillcolor='rgba(252,201,5,.05)')
    # seasonal_lower = go.Scatter(x=df_forecast['ds'],
    #                 y=df_forecast['seasonal_lower'],
    #                 fill='tonexty',
    #                 mode='none',
    #                 name='seasonal_lower',
    #                 fillcolor='rgba(252,101,5,.05)')
    # seasonal_upper = go.Scatter(x=df_forecast['ds'],
    #                 y=df_forecast['seasonal_upper'],
    #                 fill='tonexty',
    #                 mode='none',
    #                 name='seasonal_upper',
    #                 fillcolor='rgba(252,201,205,.05)')
    # offline.plot({'data': [seasonal, seasonal_lower, seasonal_upper],
    #              'layout': layout},
    #              filename='docs/testeeeeee.html')
    if ds is None:
        return "Error: routes.py:17, ds is None", 400
    return 'Open in new window', 201
if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost', port=3030)