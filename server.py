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
from flask import Flask, jsonify, request
from configs.functions import get_datasets
from statsmodels.stats import stattools
from flask_cors import CORS
from io import StringIO
from urllib.parse import urlparse
from scipy.optimize import minimize
from plotly import tools

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

def build_layout(title, x_axis_title, y_axis_title):
    """Create the plotly's layout with custom configuration

    Arguments:
        title {str} -- Layout's central title
        x_axis_title {str} -- Axis x title
        y_axis_title {str} -- Axis y title

    Returns:
        Object -- Plotly object from plotly.graph_objs
    """

    layout = go.Layout(plot_bgcolor='#2d2929',
                       paper_bgcolor='#2d2929',
                       title=title,
                       font=dict(color='rgb(255, 255, 255)', size=17),
                       legend=dict(orientation="h"),
                       yaxis=dict(title=y_axis_title),
                       xaxis=dict(title=x_axis_title))
    return layout

def var_cov_matrix(df, weigths):
    """Compute covariance matrix with respect of given weigths

    Arguments:
        df {pandas.DataFrame} -- The timeseries object
        weigths {list} -- List of weights to be used

    Returns:
        numpy.array -- The covariance matrix
    """

    sigma = np.cov(np.array(df).T, ddof=0)
    var = (np.array(weigths) * sigma * np.array(weigths).T).sum()
    return var

def calc_exp_returns(avg_return, weigths):
    """Compute the expected returns

    Arguments:
        avg_return {pandas.DataFrame} -- The average of returns
        weigths {list} -- A list of weigths

    Returns:
        array -- N dimensions array
    """

    exp_returns = avg_return.dot(weigths.T)
    return exp_returns

@app.route('/efficient_frontier', methods=['POST'])
def efficient_frontier():
    """Compute the efficient frontier given the timeseries via http post"""

    values = request.get_json()
    timeseries = values.get('timeseries')
    if timeseries == {}:
        return 'Select your portfolio'

    potfolio_size = len(timeseries) - 1
    weigths = np.random.dirichlet(alpha=np.ones(potfolio_size), size=1) # makes sure that weights sums upto 1.
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
                          x_axis_title='Risk %',
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
    return 'app/public/weights_{}.html'.format(datetime.datetime.now().date())

@app.route('/correlation', methods=['POST'])
def correlation():
    """Compute the rolling correlation and heatmap using the timeseries given via http post"""

    values = request.get_json()
    timeseries = values.get('timeseries')
    if timeseries == {}:
        return 'Select your portfolio'
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
                              x_axis_title='',
                              y_axis_title='')
        offline.plot({'data': [heatmap],
            'layout': layout},
            filename='app/public/correlation_{}_{}.html'.format(cor, datetime.datetime.now().date()))

    rolling_correlation = df.rolling(30).corr(pairwise=True)
    for col in rolling_correlation.columns:
        unstacked_df = rolling_correlation.unstack(level=1)[col]
        data = []
        for unstacked_col in unstacked_df.columns:
            if not unstacked_col == col:
                trace = go.Scatter(x=unstacked_df.index,
                                y=unstacked_df[unstacked_col],
                                name=col+'/'+unstacked_col)
                data.append(trace)
        layout = build_layout(title='{} 30 Days Rolling Correlation'.format(col),
                            x_axis_title='',
                            y_axis_title='Correlation')
        offline.plot({'data': data,
                    'layout': layout},
                    filename='app/public/rolling_corr_{}_{}.html'.format(col, datetime.datetime.now().date()))
    return 'Open /app/public/correlation_{}.html'.format(datetime.datetime.now().date())

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
                 filename='app/public/returns_{}.html'.format(datetime.datetime.now().date()))

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
                 filename='app/public/histogram_{}.html'.format(datetime.datetime.now().date()))
    return 'Open /app/public/returns_{}.html'.format(datetime.datetime.now().date())

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
                 filename='app/public/prophet_{}_{}.html'.format(datetime.datetime.now().date(), symbol))
    if ds is None:
        return "Error: routes.py:17, ds is None"
    return 'Open /app/public/prophet_{}.html'.format(datetime.datetime.now().date())

@app.route('/indicatorsDashboard', methods=['POST'])
def indicators():
    values = request.get_json()
    coin_id = values.get('coinId')
    symbol = values.get('symbol')

    if not (os.path.exists('datasets/trading_{}-BTC_{}.csv'.format(symbol, datetime.datetime.now().date()))):
        df = get_datasets(symbol, coin_id)
    else:
        df = pd.read_csv('datasets/trading_{}-BTC_{}.csv'.format(symbol, datetime.datetime.now().date()))

    # overlap dashboard
    data = [dict(type='candlestick', open=df['open'], high=df['high'],
                 low=df['low'], close=df['close'], x=df['Date'], yaxis='y2',
                 name='Price', increasing=dict(line=dict(color=INCREASING_COLOR)), decreasing=dict(line=dict(color=DECREASING_COLOR)))]
    layout=dict()
    fig = dict(data=data, layout=layout)
    # fig['layout'] = dict()
    fig['layout']['title'] = '{} Dashboard #1'.format(symbol)
    fig['layout']['plot_bgcolor'] = '#2d2929'
    fig['layout']['paper_bgcolor'] = '#2d2929'
    fig['layout']['font'] = dict(color='rgb(255, 255, 255)', size=17)
    fig['layout']['xaxis'] = dict(rangeslider=dict(visible=False), rangeselector=dict(visible=True))
    fig['layout']['yaxis'] = dict(domain=[0, 0.2], showticklabels=False)
    fig['layout']['yaxis2'] = dict(domain=[0.2, 0.8])
    fig['layout']['xaxis']['rangeselector'] = RANGESELECTOR
    fig['data'].append(dict(x=df['Date'], y=df['SMA'], type='scatter', mode='lines', yaxis='y2', name='Simple Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['WMA'], type='scatter', mode='lines', yaxis='y2', name='Weighted Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['MIDPOINT'], type='scatter', mode='lines', yaxis='y2', name='Midpoint'))
    fig['data'].append(dict(x=df['Date'], y=df['MA'], type='scatter', mode='lines', yaxis='y2', name='Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['KAMA'], type='scatter', mode='lines', yaxis='y2', name='Kaufman Adaptive Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['HT_TRENDLINE'], type='scatter', mode='lines', yaxis='y2', name='Hilbert Transform'))
    fig['data'].append(dict(x=df['Date'], y=df['EMA'], type='scatter', mode='lines', yaxis='y2', name='Exp Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['DEMA'], type='scatter', mode='lines', yaxis='y2', name='Double Moving Average'))
    fig['data'].append(dict(x=df['Date'], y=df['BBANDS_upper'], type='scatter', mode='lines', yaxis='y2', name='BBANDS_upper'))
    fig['data'].append(dict(x=df['Date'], y=df['BBANDS_middle'], type='scatter', mode='lines', yaxis='y2', name='BBANDS_middle'))
    fig['data'].append(dict(x=df['Date'], y=df['BBANDS_lower'], type='scatter', mode='lines', yaxis='y2', name='BBANDS_lower'))

    colors = []
    for i in range(len(df['close'])):
        if i != 0:
            if df['close'][i] > df['close'][i-1]:
                colors.append(INCREASING_COLOR)
            else:
                colors.append(DECREASING_COLOR)
        else:
            colors.append(DECREASING_COLOR)

    fig['data'].append(dict(x=df['Date'], y=df['volumeto'],
                            marker=dict( color=colors),
                            type='bar', yaxis='y', name='Volume'))

    offline.plot(fig, filename='app/public/overlap_{}_{}.html'.format(symbol, datetime.datetime.now().date()), validate=False)

    # plot 2 dashboard
    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['Analysis Page Views','Charts Page Views','Comments'])
    trace = go.Scatter(x=df['Date'], y=df['analysis_page_views'].pct_change(), name='Analysis Page Views', fill='tonexty', mode='none')
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['charts_page_views'].pct_change(), name='Charts Page Views', fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Bar(x=df['Date'], y=df['comments'].pct_change(), name='Comments')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Social Indicators #1'.format(symbol),
                         showlegend=False,
                         font=dict(color='rgb(255, 255, 255)', size=16),
                         paper_bgcolor='#2d2929',
                         plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/social1_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['FB Likes','FB Talking About','Influence Page Views'])
    trace = go.Scatter(x=df['Date'], y=df['fb_likes'], name='FB Likes', fill='tonexty', mode='none')
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['fb_talking_about'], name='FB Talking About', fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['influence_page_views'].pct_change(), name='influence_page_views pct change', fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Social Indicators #2'.format(symbol),
                         showlegend=False,
                         font=dict(color='rgb(255, 255, 255)', size=16),
                         paper_bgcolor='#2d2929',
                         plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/social2_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # plot 3 dashboard
    fig = tools.make_subplots(rows=4, cols=1, subplot_titles=['Followers','Forum Page Views','Markets Page Views','Overview Page Views'])
    trace = go.Bar(x=df['Date'], y=df['followers'].pct_change(), name='followers pct change')
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['forum_page_views'].pct_change(), name='forum_page_views pct change', fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['markets_page_views'].pct_change(), name='markets_page_views pct change', fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    trace = go.Scatter(x=df['Date'], y=df['overview_page_views'].pct_change(), name='overview_page_views pct change', fill='tonexty', mode='none')
    fig.append_trace(trace, 4, 1)
    fig['layout'].update(title='{} Social Indicators #3'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/social3_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # cycle indicators
    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['HT_DCPERIOD','HT_DCPHASE','HT_PHASOR_inphase'])
    trace = go.Bar(x=df['Date'], y=df['HT_DCPERIOD'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['HT_DCPHASE'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['HT_PHASOR_inphase'], fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Cycle Indicators #1'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/cycle_indicators1_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=2, cols=1, subplot_titles=['HT_SINE_sine','HT_TRENDMODE'])
    trace = go.Scatter(x=df['Date'], y=df['HT_SINE_sine'], fill='tonexty', mode='none')
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['HT_TRENDMODE'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    fig['layout'].update(title='{} Cycle Indicators #2'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/cycle_indicators2_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # momemtum indicators
    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['ADX','ADXR','APO'])
    trace = go.Bar(x=df['Date'], y=df['ADX'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['ADXR'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['APO'], fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Momemtum Indicators #1'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators1_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['AROON','CCI','CMO'])
    trace = go.Scatter(x=df['Date'], y=df['AROON_down'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['AROONOSC'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['CCI'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['CMO'], fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Momemtum Indicators #2'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators2_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['BOP','DX','MFI'])
    trace = go.Bar(x=df['Date'], y=df['BOP'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['DX'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['MFI'], fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Momemtum Indicators #3'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators3_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['MOM','PPO','ROC'])
    trace = go.Bar(x=df['Date'], y=df['MOM'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['PPO'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['ROC'], fill='tonexty', mode='none')
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Momemtum Indicators #4'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators4_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=2, cols=1, subplot_titles=['TRIX','RSI'])
    trace = go.Scatter(x=df['Date'], y=df['TRIX'], fill='tonexty', mode='none')
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['RSI'], fill='tonexty', mode='none')
    fig.append_trace(trace, 2, 1)
    fig['layout'].update(title='{} Momemtum Indicators #5'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators5_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=4, cols=1, subplot_titles=['MACD','DMI','STOCH', 'STOCHF'])
    trace = go.Scatter(x=df['Date'], y=df['MACD'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['MACD_signal'])
    fig.append_trace(trace, 1, 1)
    trace = go.Bar(x=df['Date'], y=df['MACD_hist'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['MINUS_DI'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['MINUS_DM'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['STOCH_k'])
    fig.append_trace(trace, 3, 1)
    trace = go.Scatter(x=df['Date'], y=df['STOCH_d'])
    fig.append_trace(trace, 3, 1)
    trace = go.Scatter(x=df['Date'], y=df['STOCHF_k'])
    fig.append_trace(trace, 4, 1)
    trace = go.Scatter(x=df['Date'], y=df['STOCHF_d'])
    fig.append_trace(trace, 4, 1)
    fig['layout'].update(title='{} Momemtum Indicators #6'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators6_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['STOCHRSI','ULTOSC','WILLR'])
    trace = go.Scatter(x=df['Date'], y=df['STOCHRSI_K'])
    fig.append_trace(trace, 1, 1)
    trace = go.Scatter(x=df['Date'], y=df['STOCHRSI_D'])
    fig.append_trace(trace, 1, 1)
    trace = go.Bar(x=df['Date'], y=df['ULTOSC'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['WILLR'])
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Momemtum Indicators #7'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/momemtum_indicators7_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # pattern recognition
    fig = tools.make_subplots(rows=2, cols=1, subplot_titles=['CDL2','CDL3'])
    trace = go.Scatter(x=df['Date'], y=df['CDL2CROWS'])
    fig.append_trace(trace, 1, 1)
    trace = go.Bar(x=df['Date'], y=df['CDL3BLACKCROWS'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['CDL3INSIDE'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['CDL3LINESTRIKE'])
    fig.append_trace(trace, 2, 1)
    fig['layout'].update(title='{} Pattern Recoginition'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/pattern_recognition_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # price transform
    fig = tools.make_subplots(rows=4, cols=1, subplot_titles=['WCLPRICE','ATR','NATR','TRANGE'])
    trace = go.Scatter(x=df['Date'], y=df['WCLPRICE'])
    fig.append_trace(trace, 1, 1)
    # volatility indicators
    trace = go.Bar(x=df['Date'], y=df['ATR'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['NATR'])
    fig.append_trace(trace, 3, 1)
    trace = go.Scatter(x=df['Date'], y=df['TRANGE'])
    fig.append_trace(trace, 4, 1)
    fig['layout'].update(title='{} Volatility Indicators'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/volatility_indicators_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # statistic funcitons
    fig = tools.make_subplots(rows=5, cols=1, subplot_titles=['BETA','CORREL','STDDEV','TSF','VAR'])
    trace = go.Scatter(x=df['Date'], y=df['BETA'])
    fig.append_trace(trace, 1, 1)
    trace = go.Bar(x=df['Date'], y=df['CORREL'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['STDDEV'])
    fig.append_trace(trace, 3, 1)
    trace = go.Scatter(x=df['Date'], y=df['TSF'])
    fig.append_trace(trace, 4, 1)
    trace = go.Scatter(x=df['Date'], y=df['VAR'])
    fig.append_trace(trace, 5, 1)
    fig['layout'].update(title='{} Statistic Funcitons'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/statistic_funcitons_{}_{}.html'.format(symbol, datetime.datetime.now().date()))

    # volume indicators
    fig = tools.make_subplots(rows=3, cols=1, subplot_titles=['AD','ADOSC','OBV'])
    trace = go.Scatter(x=df['Date'], y=df['AD'])
    fig.append_trace(trace, 1, 1)
    trace = go.Bar(x=df['Date'], y=df['ADOSC'])
    fig.append_trace(trace, 2, 1)
    trace = go.Scatter(x=df['Date'], y=df['OBV'])
    fig.append_trace(trace, 3, 1)
    fig['layout'].update(title='{} Volume Indicators'.format(symbol),
                         showlegend=False,
                        font=dict(color='rgb(255, 255, 255)', size=16),
                        paper_bgcolor='#2d2929',
                        plot_bgcolor='#2d2929')
    offline.plot(fig, filename='app/public/volume_indicators_{}_{}.html'.format(symbol, datetime.datetime.now().date()))


if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost', port=3030)