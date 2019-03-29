import pandas as pd
import json, matplotlib, fbprophet, os
from flask import Flask, jsonify, request
from flask_cors import CORS
import gzip
from io import StringIO
from urllib.parse import urlparse

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
    print(df_forecast.keys())
    if ds is None:
        return "Error: routes.py:17, ds is None", 400
    return jsonify({
        'ds': df_forecast.ds.tolist(),
        'y': y,
        'yhat': df_forecast['yhat'].tolist(),
        'trend': df_forecast['trend'].tolist(),
        'yhat_upper': df_forecast['yhat_upper'].tolist(),
        'yhat_lower': df_forecast['yhat_lower'].tolist()
    }), 201
if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost', port=3030)