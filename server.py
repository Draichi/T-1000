import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.offline as offline
import json
import matplotlib
import fbprophet
import os
import ad
import gzip
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from io import StringIO
from urllib.parse import urlparse
from scipy.optimize import minimize
from plotly import tools

# TODO
# X transformar os botoes em ações relativas aos symbols selecionados
# X add + indicators no cryptocompare_api.py

app = Flask(__name__)
CORS(app)

def build_layout(title, x_axis_title, y_axis_title):
    layout = go.Layout(plot_bgcolor='#2d2929',
                       paper_bgcolor='#2d2929',
                       title=title,
                       font=dict(color='rgb(255, 255, 255)', size=17),
                       legend=dict(orientation="h"),
                       yaxis=dict(title=y_axis_title),
                       xaxis=dict(title=x_axis_title))
    return layout

def var_cov_matrix(df, weigths):
    sigma = np.cov(np.array(df).T, ddof=0) # covariance
    var = (np.array(weigths) * sigma * np.array(weigths).T).sum()
    return var

def calc_exp_returns(avg_return, weigths):
    exp_returns = avg_return.dot(weigths.T)
    return exp_returns

@app.route('/efficient_frontier', methods=['POST'])
def efficient_frontier():
    values = request.get_json()
    timeseries = values.get('timeseries')

    potfolio_size = len(timeseries) - 1
    weigths = np.random.dirichlet(alpha=np.ones(potfolio_size), size=1) # makes sure that weights sums upto 1.
    EXP_RETURN_CONSTRAINT = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
    BOUNDS = ((0.0, 1.),) * potfolio_size # bounds of the problem

    df = pd.DataFrame(timeseries)
    df.set_index('date', inplace=True)
    df = df.pct_change()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    returns = df.mean()
    results_comparison_dict = {}
    for i in range(len(EXP_RETURN_CONSTRAINT)):
        res = minimize(
            # object function defined here
            fun=lambda x: var_cov_matrix(df, x),
            x0=weigths,
            method='SLSQP',
            # jacobian using automatic differentiation
            jac=ad.gh(lambda x: var_cov_matrix(df, x))[0],
            bounds=BOUNDS,
            options={'disp': True, 'ftol': 1e-20, 'maxiter': 1000},
            constraints=[{'type': 'eq', 'fun': lambda x: sum(x) -1.0},
                        {'type': 'eq', 'fun': lambda x: calc_exp_returns(returns, x) - EXP_RETURN_CONSTRAINT[i]}])
        return_key = round(EXP_RETURN_CONSTRAINT[i]*100, 2)
        results_comparison_dict.update({return_key: [res.fun, res.x]})

    z = [[x, results_comparison_dict[x][0]*100] for x in results_comparison_dict]
    objects, risk_vals = list(zip(*z))
    # t_pos = np.arange(len(objects))
    data = go.Scatter(x=risk_vals, y=objects, mode='markers', marker=dict(size=20))
    layout = build_layout(title='Risk associated with different levels of returns',
                          x_axis_title='Risk %'
                          y_axis_title='Expected returns %')
    offline.plot({'data': [data], 'layout': layout},
                 filename='app/public/efficient_frontier_{}.html'.format(datetime.datetime.now().date()))

    keys = sorted(list(results_comparison_dict.keys()))
    index = 0
    x_itemns = list(df.columns)
    # x_itemns.remove('date')

    fig = tools.make_subplots(rows=4, cols=4, subplot_titles=(keys))
    for i in range(1,5):
        for j in range(1,5):
            trace = go.Bar(x=x_itemns, y=results_comparison_dict[keys[index]][1], name='{} %'.format(keys[index]))
            fig.add_trace(trace, row=i, col=j)
            index += 1
    fig['layout'].update(title='Weights per asset at different expected returns (%)',
                         font=dict(color='rgb(255, 255, 255)', size=14),
                         paper_bgcolor='#2d2929',
                         plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/weights_{}.html'.format(datetime.datetime.now().date()))
    return 'app/public/weights_{}.html'.format(datetime.datetime.now().date()), 201

@app.route('/correlation', methods=['POST'])
def correlation():
    values = request.get_json()
    timeseries = values.get('timeseries')
    df = pd.DataFrame(timeseries)
    df.set_index('date', inplace=True)
    for cor in ['pearson', 'kendall', 'spearman']:
        heatmap = go.Heatmap(z=df.pct_change().corr(method=cor).values,
                            x=df.pct_change().columns,
                            y=df.pct_change().columns,
                            colorscale=[[0, 'rgb(255,0,0)'], [1, 'rgb(0,255,0)']],
                            zmin=-1.0,
                            zmax=1.0)
        layout = build_layout(title='{} Correlation'.format(cor.title()),
                              x_axis_title=''
                              y_axis_title='')
        offline.plot({'data': [heatmap],
            'layout': layout},
            filename='app/public/correlation_{}_{}.html'.format(cor, datetime.datetime.now().date()))
    return 'Open /app/public/correlation_{}.html'.format(datetime.datetime.now().date()), 201

@app.route('/returns', methods=['POST'])
def returns():
    values = request.get_json()
    timeseries = values.get('timeseries')
    df = pd.DataFrame(timeseries)
    df.set_index('date', inplace=True)
    data = []
    for coin in df.columns:
        trace = go.Scatter(x=df.index,
                           y=df[coin].pct_change()*100,
                           name=coin)
        data.append(trace)
    layout = build_layout(title='Portfolio Returns',
                          x_axis_title=''
                          y_axis_title='Retuns (%)')
    offline.plot({'data': data,
                 'layout': layout},
                 filename='app/public/returns_{}.html'.format(datetime.datetime.now().date()))
    return 'Open /app/public/returns_{}.html'.format(datetime.datetime.now().date()), 201

@app.route('/prophet', methods = ['POST'])
def prophet():
    values = request.get_json()
    dataset = values.get('dataset')
    ds = dataset['ds']
    y = dataset['y']
    changepoint_prior_scale = values.get('changepoint_prior_scale')
    forecast_days = values.get('forecast_days')
    symbol = values.get('symbol')
    df = pd.DataFrame(dataset)
    #------------------------------------------------------------->
    df_prophet = fbprophet.Prophet(changepoint_prior_scale=changepoint_prior_scale)
    df_prophet.fit(df)
    #------------------------------------------------------------->
    df_forecast = df_prophet.make_future_dataframe(periods=int(forecast_days))
    df_forecast = df_prophet.predict(df_forecast)
    df_forecast.to_json(orient='columns')
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
    layout = build_layout(title='Propheting {} day(s) of {} (Changepoint: {})'.format(forecast_days, symbol, changepoint_prior_scale),
                          x_axis_title=''
                          y_axis_title='Price (BTC)')
    offline.plot({'data': [y, yhat, yhat_lower, yhat_upper],'layout': layout},
                 filename='app/public/prophet_{}_{}.html'.format(datetime.datetime.now().date(), symbol))
    if ds is None:
        return "Error: routes.py:17, ds is None", 400
    return 'Open /app/public/prophet_{}.html'.format(datetime.datetime.now().date()), 201

if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost', port=3030)