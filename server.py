"""Server of cryptocurrency_prediction with portfolio functions.

Example:
    $ python server.py

Lucas Draichi
2018
"""

import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.offline as offline
import json
import fbprophet
import os
import ad
import gzip
import datetime
import requests
import talib
from flask import Flask, jsonify, request
from configs.functions import get_datasets, calc_exp_returns, build_layout, var_cov_matrix
from statsmodels.stats import stattools
from flask_cors import CORS
from io import StringIO
from urllib.parse import urlparse
from scipy.optimize import minimize
from plotly import tools

INDICATORS = {
    'adx': {
        'timeperiod': 14
    }
}
TRAIN_SIZE = 0.5 # 50% to train
WALLET_BTC = 1.0
INCREASING_COLOR = 'rgb(41, 127, 255)'
DECREASING_COLOR = 'rgb(255, 170, 0)'
EXP_RETURN_CONSTRAINT = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
RANGESELECTOR = dict(visibe=True, x = 0, y = 0.9, bgcolor = 'rgba(150, 200, 250, 0.4)', font=dict(size=13),
                     buttons=list([dict(count=1, label='1 day', step='day', stepmode='backward'),
                                   dict(count=7, label='7 days', step='day', stepmode='backward'),
                                   dict(count=15, label='15 days', step='day', stepmode='backward'),
                                   dict(count=1, label='1 mo', step='month', stepmode='backward'),
                                   dict(step='all')]))
app = Flask(__name__)
CORS(app)

@app.route('/returns', methods=['POST'])
def returns():
    """Compute and plot the returns. Timeseries must be given via http post"""

    values = request.get_json()
    timeseries = values.get('timeseries')
    if timeseries == {}:
        return 'Select your portfolio'
    df = pd.DataFrame(timeseries)
    df.set_index('date', inplace=True)

    data = []
    returns_list = []
    for coin in df.columns:
        returns = df[coin].pct_change()[1:]
        trace = go.Scatter(x=df.index,
                           y=returns*100,
                           name=coin)
        data.append(trace)
        returns_list.append(returns)
    layout = build_layout(title='Portfolio Returns',
                          x_axis_title='',
                          y_axis_title='Retuns (%)')
    offline.plot({'data': data,
                 'layout': layout},
                 filename='app/public/returns.html')

    portfolio_returns = sum(returns_list)
    sample_mean = np.mean(portfolio_returns)
    sample_std_dev = np.std(portfolio_returns)
    _, pvalue, _, _ = stattools.jarque_bera(portfolio_returns)
    layout = build_layout(title='The returns are likely normal.' if pvalue > 0.05 else 'The returns are likely not normal.',
                            x_axis_title='Value',
                            y_axis_title='Occurrences')
    x = np.linspace(-(sample_mean + 4 * sample_std_dev), (sample_mean + 4 * sample_std_dev), len(portfolio_returns))
    sample_distribution = ((1/np.sqrt(sample_std_dev * sample_std_dev * 2 * np.pi)) * np.exp(-(x - sample_mean)*(x - sample_mean) / (2 * sample_std_dev * sample_std_dev)))
    data = [go.Histogram(x=portfolio_returns, nbinsx=len(portfolio_returns), name='Returns'), go.Scatter(x=x, y=sample_distribution, name='Normal Distribution')]
    offline.plot({'data': data,
                 'layout': layout},
                 filename='app/public/histogram.html')


    for cor in ['pearson', 'kendall', 'spearman']:
        heatmap = go.Heatmap(z=df.pct_change().corr(method=cor).values,
                            x=df.pct_change().columns,
                            y=df.pct_change().columns,
                            colorscale=[[0, 'rgb(255,0,0)'], [1, 'rgb(0,255,0)']],
                            zmin=-1.0,
                            zmax=1.0)
        layout = build_layout(title='{} Correlation'.format(cor.title()),
                              x_axis_title='',
                              y_axis_title='')
        offline.plot({'data': [heatmap],
            'layout': layout},
            filename='app/public/correlation_{}.html'.format(cor))

    #
    # ROLLING CORRELLATION
    #
    # rolling_correlation = df.rolling(30).corr(pairwise=True)
    # for col in rolling_correlation.columns:
    #     unstacked_df = rolling_correlation.unstack(level=1)[col]
    #     data = []
    #     for unstacked_col in unstacked_df.columns:
    #         if not unstacked_col == col:
    #             trace = go.Scatter(x=unstacked_df.index,
    #                             y=unstacked_df[unstacked_col],
    #                             name=col+'/'+unstacked_col)
    #             data.append(trace)
    #     layout = build_layout(title='{} 30 Days Rolling Correlation'.format(col),
    #                         x_axis_title='',
    #                         y_axis_title='Correlation')
    #     offline.plot({'data': data,
    #                 'layout': layout},
    #                 filename='app/public/rolling_corr_{}.html'.format(col))

    potfolio_size = len(timeseries) - 1
    weigths = np.random.dirichlet(alpha=np.ones(potfolio_size), size=1) # makes sure that weights sums upto 1.
    BOUNDS = ((0.0, 1.),) * potfolio_size # bounds of the problem

    #
    # HERE THE DF CHANGES
    #
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
                          x_axis_title='Risk %',
                          y_axis_title='Expected returns %')
    offline.plot({'data': [data], 'layout': layout},
                 filename='app/public/efficient_frontier.html')

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
    offline.plot(fig, filename='app/public/weights.html')
    return 'ok'
    # return 'app/public/weights_{}.html'.format(datetime.datetime.now().date())

@app.route('/prophet', methods = ['POST'])
def prophet():
    """Compute and plot a 'prophecy' of a given coin. Timeserie must be given via http post"""

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
                          x_axis_title='',
                          y_axis_title='Price (BTC)')
    offline.plot({'data': [y, yhat, yhat_lower, yhat_upper],'layout': layout},
                 filename='app/public/prophet_{}.html'.format(symbol))
    return 'ok'

@app.route('/indicatorsDashboard', methods=['POST'])
def indicators():
    values = request.get_json()
    timeseries = values.get('timeseries')
    df = pd.DataFrame(timeseries)
    df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
    df.drop('time', axis=1, inplace=True)
    df.set_index('Date', inplace=True)

    np_keys = {}
    pairs = []
    for key in df.keys():
        np_keys[key] = np.array(df[key]) # build the np dict
        name = key.split('_')[0]
        if name not in pairs: # build the pairs list
            pairs.append(name)

    for pair in pairs:
        df.loc[:, pair + '_ADX'] = talib.ADX(np_keys[pair + '_high'], np_keys[pair + '_low'], np_keys[pair + '_close'], timeperiod=INDICATORS['adx']['timeperiod'])
    
    
    # WIP


    print(df)
    return'ok'
    timeseries.pop('pair', None)
    df = pd.DataFrame(timeseries)
    df['Date'] = pd.to_datetime(df['time'], utc=True, unit='s')
    df.drop('time', axis=1, inplace=True)
    open_price, high, low, close = np.array(df['open']), np.array(df['high']), np.array(df['low']), np.array(df['close'])
    volume = np.array(df['volume'])

    df.loc[:, 'BBANDS_upper'], df.loc[:, 'BBANDS_middle'], df.loc[:, 'BBANDS_lower'] = talib.BBANDS(close, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)
    df.loc[:, 'HT_DCPERIOD'] = talib.HT_DCPERIOD(close)
    df.loc[:, 'ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df.loc[:, 'MOM'] = talib.MOM(close, timeperiod=10)
    df.loc[:, 'RSI'] = talib.RSI(close, timeperiod=14)
    df.loc[:, 'wallet_btc'] = WALLET_BTC
    df.loc[:, 'wallet_symbol'] = 0.0
    df.dropna(inplace=True)
    df.set_index('Date', inplace=True)

    train_size = round(len(df) * TRAIN_SIZE)
    df_train = df[:train_size]
    df_train.name = 'Train'
    df_rollout = df[train_size:]
    df_rollout.name = 'Rollout'
    df_train.to_csv('datasets/bot_train_{}.csv'.format(symbol))
    df_rollout.to_csv('datasets/bot_rollout_{}.csv'.format(symbol))

    for dataframe in [df_train, df_rollout]:
        data = [dict(type='candlestick', open=dataframe['open'], high=dataframe['high'],
                    low=dataframe['low'], close=dataframe['close'], x=dataframe.index, yaxis='y2',
                    name='Price', increasing=dict(line=dict(color=INCREASING_COLOR)), decreasing=dict(line=dict(color=DECREASING_COLOR)))]
        layout=dict()
        fig = dict(data=data, layout=layout)
        fig['layout']['title'] = '{} {} Data Dashboard'.format(dataframe.name, symbol)
        fig['layout']['plot_bgcolor'] = '#2d2929'
        fig['layout']['paper_bgcolor'] = '#2d2929'
        fig['layout']['font'] = dict(color='rgb(255, 255, 255)', size=17)
        fig['layout']['xaxis'] = dict(rangeslider=dict(visible=False), rangeselector=dict(visible=True))
        fig['layout']['yaxis'] = dict(domain=[0, 0.2], showticklabels=False)
        fig['layout']['yaxis2'] = dict(domain=[0.2, 0.8])
        fig['layout']['xaxis']['rangeselector'] = RANGESELECTOR
        fig['data'].append(dict(x=dataframe.index, y=dataframe['BBANDS_upper'], type='scatter', mode='lines', yaxis='y2', name='BBANDS_upper'))
        fig['data'].append(dict(x=dataframe.index, y=dataframe['BBANDS_middle'], type='scatter', mode='none', fill='tonexty', yaxis='y2', name='BBANDS_middle'))
        fig['data'].append(dict(x=dataframe.index, y=dataframe['BBANDS_lower'], type='scatter', mode='none', fill='tonexty', yaxis='y2', name='BBANDS_lower'))
        colors = []
        for i in range(len(dataframe['close'])):
            if i != 0:
                if dataframe['close'][i] > dataframe['close'][i-1]:
                    colors.append(INCREASING_COLOR)
                else:
                    colors.append(DECREASING_COLOR)
            else:
                colors.append(DECREASING_COLOR)
        fig['data'].append(dict(x=dataframe.index, y=dataframe['volume'],
                                marker=dict( color=colors),
                                type='bar', yaxis='y', name='Volume'))
        offline.plot(fig, filename='app/public/{}_{}_data.html'.format(dataframe.name, symbol), validate=False)

        fig = tools.make_subplots(rows=4, cols=1, subplot_titles=['HT_DCPERIOD','ADX','MOM', 'RSI'])
        trace = go.Scatter(x=dataframe.index, y=dataframe['HT_DCPERIOD'])
        fig.append_trace(trace, 1, 1)
        trace = go.Scatter(x=dataframe.index, y=dataframe['ADX'])
        fig.append_trace(trace, 2, 1)
        trace = go.Bar(x=dataframe.index, y=dataframe['MOM'])
        fig.append_trace(trace, 3, 1)
        trace = go.Scatter(x=dataframe.index, y=dataframe['RSI'])
        fig.append_trace(trace, 4, 1)
        fig['layout'].update(title='{} {} Indicators'.format(dataframe.name, symbol),
                            showlegend=False,
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929')
        offline.plot(fig, filename='app/public/{}_{}_indicators.html'.format(dataframe.name, symbol))

    return 'ok'

if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost', port=3030)