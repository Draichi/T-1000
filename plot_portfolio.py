"""Plot portfolio

Plot diffrent portfolio informations

Run:
    python plot_portfolio.py --help
"""

import configs.get_datasets
import pandas as pd
import numpy as np
from configs.vars import coins, days, todays_day, todays_month, currency, PATH_TO_COIN_FILE, \
    PATH_TO_CORRELATION_FILE, PATH_TO_PCT_CORRELATION_FILE, PATH_TO_WEIGHTS_FILE
# from configs.functions import print_dollar
import plotly.graph_objs as go
import plotly.offline as offline
import fbprophet
import os
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import ad 
import random
from plotly import tools
import pickle
np.random.seed(10)
weigths = np.random.dirichlet(alpha=np.ones(len(coins)), size=1) # makes sure that weights sums upto 1.
exp_return_constraint = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
#---------------------------------------------------------------------------------->
def _build_layout(title, x_axis_title=None, y_axis_title=None, y_axis_type=None):
    """[summary]
    
    Arguments:
        title {[type]} -- [description]
        y_axis_title {[type]} -- [description]
    
    Keyword Arguments:
        y_axis_type {[type]} -- [description] (default: {None})
    
    Returns:
        [type] -- [description]"""
    layout = go.Layout(plot_bgcolor='#2d2929',
                       paper_bgcolor='#2d2929',
                       title=title,
                       font=dict(color='rgb(255, 255, 255)', size=17),
                       legend=dict(orientation="h"),
                       yaxis=dict(title=y_axis_title, type=y_axis_type),
                       xaxis=dict(title=x_axis_title))
    return layout
#---------------------------------------------------------------------------------->
def _build_data(pct_change=False):
    """[summary]
    
    Keyword Arguments:
        pct_change {bool} -- [description] (default: {False})
    
    Returns:
        [type] -- [description]"""
    data = []
    for i, coin in enumerate(coins):
        df = pd.read_csv(PATH_TO_COIN_FILE[i])
        trace = go.Scatter(x=df.date,
                           y=df['prices'].pct_change()*100 if pct_change else df['prices'],
                           name = str(coin).upper())
        data.append(trace)
    return data
#---------------------------------------------------------------------------------->

def _build_correlation_df(pct_change=False):
    if not pct_change:
        if not (os.path.exists(PATH_TO_CORRELATION_FILE)):
            base_df = pd.read_csv(PATH_TO_COIN_FILE[0])
            for i, coin in enumerate(coins):
                df = pd.read_csv(PATH_TO_COIN_FILE[i])
                base_df[coin] = df['prices']
            base_df.set_index('date', inplace=True)
            base_df.drop(['market_caps','prices','total_volumes'], 1, inplace=True)
            base_df.to_csv(PATH_TO_CORRELATION_FILE)
        else:
            base_df = pd.read_csv(PATH_TO_CORRELATION_FILE)
            base_df.set_index('date', inplace=True)
        return base_df

    else:
        if not (os.path.exists(PATH_TO_PCT_CORRELATION_FILE)):
            df = _build_correlation_df()
            df = df.pct_change()
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna()
            df.to_csv(PATH_TO_PCT_CORRELATION_FILE)
        else:
            df = pd.read_csv(PATH_TO_PCT_CORRELATION_FILE)
            df = df.set_index('date')
        return df 
#---------------------------------------------------------------------------------->

def calc_exp_returns(avg_return, weigths):
    exp_returns = avg_return.dot(weigths.T)
    return exp_returns
#---------------------------------------------------------------------------------->

def var_cov_matrix(df, weigths):
    sigma = np.cov(np.array(df).T, ddof=0) # covariance
    var = (np.array(weigths) * sigma * np.array(weigths).T).sum()
    return var
#---------------------------------------------------------------------------------->

def optimize():
    df = _build_correlation_df(pct_change=True)
    returns = df.mean()

    bounds = ((0.0, 1.),) * len(coins) # bounds of the problem
    # [0.7%, 0.6% , 0.5% ... 0.1%] returns
    # exp_return_constraint = [ 0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06,0.05,0.04,0.03]
    results_comparison_dict = {}
    for i in range(len(exp_return_constraint)):
        res = minimize(
            # object function defined here
            lambda x: var_cov_matrix(df, x),
            weigths,
            method='SLSQP',
            # jacobian using automatic differentiation
            jac=ad.gh(lambda x: var_cov_matrix(df, x))[0],
            bounds=bounds,
            options={'disp': True, 'ftol': 1e-20, 'maxiter': 1000},
            constraints=[{'type': 'eq', 'fun': lambda x: sum(x) -1.0},
                        {'type': 'eq', 'fun': lambda x: calc_exp_returns(returns, x) - exp_return_constraint[i]}])
        return_key = round(exp_return_constraint[i]*100, 2)
        results_comparison_dict.update({return_key: [res.fun, res.x]})
    return res, results_comparison_dict
#---------------------------------------------------------------------------------->

def plot_efficient_frontier(comparison):
    z = [[x, comparison[x][0]*100] for x in comparison]
    objects, risk_vals = list(zip(*z))
    # t_pos = np.arange(len(objects))
    data = go.Scatter(x=risk_vals, y=objects, mode='markers', marker=dict(size=20))
    plot(data=[data],
         layout=_build_layout(title='Risk associated with different levels of returns',
                            y_axis_title='Expected returns %',
                            x_axis_title='Risk %'),
             file_name='efficient_frontier')
#---------------------------------------------------------------------------------->
def plot_weights_per_asset(comparisson):
    keys = sorted(list(comparisson.keys()))
    index = 0
    fig = tools.make_subplots(rows=4, cols=4, subplot_titles=(keys))
    for i in range(1,5):
        for j in range(1,5):
            trace = go.Bar(x=coins, y=comparisson[keys[index]][1], name=keys[index])
            fig.append_trace(trace, i, j)
            index += 1
    fig['layout'].update(title='Weights per asset at different expected returns (%)',
                         font=dict(color='rgb(255, 255, 255)'),
                         paper_bgcolor='#2d2929',
                         plot_bgcolor='#2d2929')
    offline.plot(fig, filename='weights.html')
#---------------------------------------------------------------------------------->
def plot(data, layout, file_name):
    """Plot the data according to data and layout functions.
    
    Arguments:
        title {str} -- Graph title
        y_axis_title {str} -- Y axis title
    
    Keyword Arguments:
        pct_change {bool} -- Price is shown in percent of change (default: {False})
        y_axis_type {str} -- Scale is linear or log (default: {None})
    
    """
    offline.plot({'data': data,
                 'layout': layout},
                 filename=file_name + '-' + str(todays_day) + '_' + str(todays_month) + '-' + currency + '.html')
#---------------------------------------------------------------------------------->
def main():
    """Run each code with respect to each flag
    """
    if FLAGS.change:
        plot(data=_build_data(pct_change=True),
             layout=_build_layout(title='Portfolio Change in {} Days'.format(days),
                                  y_axis_title='Change (%)'),
             file_name='pct_change')
#---------------------------------------------------------------------------------->
    if FLAGS.linear or FLAGS.log:
        plot(data=_build_data(),
             layout=_build_layout(title='Portfolio {} in {} Days'.format('Linear' if FLAGS.linear 
                                                                         else 'Log Scale', days),
                                  y_axis_title='Price ({})'.format(currency.upper()),
                                  y_axis_type='linear' if FLAGS.linear else 'log'),
             file_name='linear' if FLAGS.linear else 'log')
#---------------------------------------------------------------------------------->
    if FLAGS.forecast_coin and FLAGS.forecast_days and FLAGS.forecast_scale:
        df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day,
                                                               todays_month,
                                                               FLAGS.forecast_coin,
                                                               days,
                                                               currency))
        df['ds'] = df['date']
        df['y'] = df['prices']
        df = df[['ds', 'y']]
        df_prophet = fbprophet.Prophet(changepoint_prior_scale=FLAGS.forecast_scale)
        df_prophet.fit(df)
        df_forecast = df_prophet.make_future_dataframe(periods=int(FLAGS.forecast_days))
        df_forecast = df_prophet.predict(df_forecast)
        data = [
            go.Scatter(x=df['ds'], y=df['y'], name='Price', line=dict(color='#94B7F5')),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='yhat'),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_upper'], fill='tonexty',
                       mode='none', name='yhat_upper', fillcolor='rgba(0,201,253,.21)'),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_lower'], fill='tonexty',
                       mode='none', name='yhat_lower', fillcolor='rgba(252,201,5,.05)'),
        ]
        plot(data=data,
             layout=_build_layout(title='{} Days of {} Forecast'.format(FLAGS.forecast_days,
                                                                        currency.upper()),
                                  y_axis_title='Price ({})'.format(currency.upper())),
             file_name='forecast')
#---------------------------------------------------------------------------------->
    if FLAGS.correlation:
        base_df = _build_correlation_df()
        heatmap = go.Heatmap(
            z=base_df.pct_change().corr(method=FLAGS.correlation_method).values,
            x=base_df.pct_change().columns,
            y=base_df.pct_change().columns,
            colorbar=dict(title='Pearson Coefficient'),
            colorscale=[[0, 'rgb(255,0,0)'], [1, 'rgb(0,255,0)']],
            zmin=-1.0,
            zmax=1.0
        )
        plot(data=[heatmap],
             layout=_build_layout(title='{} Correlation Heatmap - {} days'.format(FLAGS.correlation, days).title()),
             file_name='correlation')
#---------------------------------------------------------------------------------->
    if FLAGS.efficient_frontier:
        if not (os.path.exists(PATH_TO_WEIGHTS_FILE)):

        # PORTFOLIO OPTIMIZATION AND RESULTS
            res, comparison = optimize()
            with open(PATH_TO_WEIGHTS_FILE, "wb") as fp:
                pickle.dump(comparison, fp)
        else:
            with open(PATH_TO_WEIGHTS_FILE, "rb") as fp:
                comparison = pickle.load(fp)
        plot_efficient_frontier(comparison)
        plot_weights_per_asset(comparison)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
    parser.add_argument('--correlation_method', type=str, const='pearson', nargs='?', default='pearson', help='Choose the method {pearson, kendall, spearman}')
    parser.add_argument('--correlation', action='store_true', help='Plot correlation heatmap')
    parser.add_argument('--efficient_frontier', action='store_true', help='Plot portfolio efficient frontier')
    parser.add_argument('--change', action='store_true', help='Plot portfolio percent change')
    parser.add_argument('--linear', action='store_true', help='plot portfolio linear prices')
    parser.add_argument('--log', action='store_true', help='Plot portfolio log prices')
    parser.add_argument('--forecast_coin', '-fc', type=str, help='Coin name')
    parser.add_argument('--forecast_days', '-fd', type=int, default=5, help='How many days to forecast')
    parser.add_argument('--forecast_scale', '-fs', type=float, default=0.1, help='Changepoint priot scale [0.1 ~ 0.9]')
    FLAGS = parser.parse_args()
    main()
    # print_dollar()