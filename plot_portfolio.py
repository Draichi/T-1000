"""Plot portfolio

Plot diffrent portfolio informations

Run:
    python plot_portfolio.py --help

Written in 2018 - Lucas Draichi
"""
# TODO:
# - decorators
#  X fazer com que a correlation seja gerada qnd morkovitza for instanciado
#   - documentar as funcoes
#   X plotar com o plotly 
#   - tornnar o tamanho do plot dinamico em relaçao a quantidade de exp_return_constants
# correlation methods: {pearson, kendall, spearman} 
#- correlation or covariance?
#- Dirichlet distribution.
#- from sklearn.preprocessing import normalize
#  normalizing an array:
#    >>> x = np.array([1.0, -1.0, 5, 10])
#    >>> array([ 1., -1.,  5., 10.])
#    >>> norm = normalize(x[:,np.newaxis], axis=0).ravel()
#    >>> array([ 0.08873565, -0.08873565,  0.44367825,  0.88735651])

#
def main():
    """Run each code with respect to each flag"""
    if FLAGS.portfolio_change:
        plot(data=_build_data(pct_change=True),
             layout=_build_layout(title='Portfolio Change in {} Days'.format(days),
                                  y_axis_title='Change (%)'),
             file_name='pct_change')
#----------------------------------------------------------------------------------------------------------------->
    # if FLAGS.portfolio_linear or FLAGS.portfolio_log:	
    #     plot(data=_build_data(),
    #          layout=_build_layout(title='Portfolio {}'.format('Linear' if FLAGS.portfolio_linear 	
    #                                                                      else 'Log Scale'),	
    #                               y_axis_title='Price ({})'.format(TIME_INTERVAL.upper()),	
    #                               y_axis_type='linear' if FLAGS.portfolio_linear else 'log'),	
    #          file_name='linear' if FLAGS.portfolio_linear else 'log')
#----------------------------------------------------------------------------------------------------------------->
    if FLAGS.plot_coin:
        df = pd.read_csv('datasets/{}_{}_{}_{}.csv'.format(FLAGS.plot_coin.upper(), TIME_INTERVAL, FROM_DATE, TO_DATE))
        
        # DASHBOARD MOMENTUM
        fig = tools.make_subplots(rows=3, cols=2, subplot_titles=['Price (Altcoins)', 'Price (BTC)', 'Price Change 24h', 'Price Change 7d', 'MACD', 'Momentum'])
        cols_axis_x = [col for col in df.columns if col not in ['Date', 'Coin']]
        for key in df[cols_axis_x]:
            name = str(key[:25])
            if key in PRICE_GROUP_1:
                trace = go.Scatter(x=df.Date, y=df[key], name=name, fill='tozeroy')
                fig.append_trace(trace, 1, 1)
            if key in PRICE_GROUP_2:
                trace = go.Scatter(x=df.Date, y=df[key], name=name, fill='tozeroy')
                fig.append_trace(trace, 1, 2)
            if key in PRICE_CHANGE_24:
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 2, 1)
            if key in PRICE_CHANGE_7D:
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 2, 2)
            if key in MACD:
                if key == 'macdhist_USD':
                    trace = go.Bar(x=df.Date, y=df[key], name=name)
                    fig.append_trace(trace, 3, 1)
                if key == 'macdsignal_USD' or key == 'macd_USD':
                    trace = go.Scatter(x=df.Date, y=df[key], name=name)
                    fig.append_trace(trace, 3, 1)
            if key in MOMENTUM_IND:
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 3, 2)
        fig['layout'].update(title='Dashboard: Momentum - {}'.format(FLAGS.plot_coin.upper()),
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929')
        offline.plot(fig, filename='docs/dashboard_{}_momentum.html'.format(FLAGS.plot_coin))

        # DASHBOARD HYPE
        fig = tools.make_subplots(rows=3, cols=2, subplot_titles=['Marketcap / Telegram hype', 'Marketcap / Twitter hype', 'Telegram Hype', 'Telegram Mood (average value by one message)', 'Twitter Hype 24h', 'Wikipedia views 30d'])
        cols_axis_x = [col for col in df.columns if col not in ['Date', 'Coin']]
        for key in df[cols_axis_x]:
            name = str(key[:25])
            if key == 'Marketcap / Telegram hype':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 1, 1)
            if key == 'Marketcap / Twitter hype':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 1, 2)
            if key == 'Telegram Hype':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 2, 1)
            if key == 'Telegram Mood (average value by one message)':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 2, 2)
            if key == 'Twitter Hype 24h':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 3, 1)
            if key == 'Wikipedia views 30d':
                trace = go.Bar(x=df.Date, y=df[key], name=name)
                fig.append_trace(trace, 3, 2)
        fig['layout'].update(title='Dashboard: Hype - {}'.format(FLAGS.plot_coin.upper()),
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929')
        offline.plot(fig, filename='docs/dashboard_{}_hype.html'.format(FLAGS.plot_coin))

        # DASHBOARD PROPHET
        fig = tools.make_subplots(rows=3, cols=2, subplot_titles=['Price $ Prophet 0.05', 'Price $ Prophet 0.15', 'Price +/- 24h $ Prophet 0.05', 'Price +/- 24h $ Prophet 0.15', 'Price BTC Prophet 0.05', 'Price BTC Prophet 0.15'])
        for i, scale in enumerate([0.05, 0.15]):
            for ii, column in enumerate(['Price $', 'Price +/- 24h $', 'Price BTC']):
                column_name = df.rename(index=str, columns={'Date': 'ds', column: 'y'})
                y, yhat, yhat_upper, yhat_lower = make_prophecy(scale, column_name[['ds', 'y']], 15, column)
                fig.append_trace(y, ii+1 , i+1)
                fig.append_trace(yhat, ii+1 , i+1)
                fig.append_trace(yhat_upper, ii+1 , i+1)
                fig.append_trace(yhat_lower, ii+1 , i+1)
        fig['layout'].update(title='Dashboard: Prophet - {}'.format(FLAGS.plot_coin.upper()),
                            font=dict(color='rgb(255, 255, 255)', size=16),
                            paper_bgcolor='#2d2929',
                            plot_bgcolor='#2d2929',
                            showlegend=False)
        offline.plot(fig, filename='docs/dashboard_{}_prophet.html'.format(FLAGS.plot_coin.upper()))

#---------------------------------------------------------------------------------->
    if FLAGS.correlation:
        base_df = _build_correlation_df()
        for cor in ['pearson', 'kendall', 'spearman']:
            heatmap = go.Heatmap(z=base_df.pct_change().corr(method=cor).values,
                                x=base_df.pct_change().columns,
                                y=base_df.pct_change().columns,
                                colorscale=[[0, 'rgb(255,0,0)'], [1, 'rgb(0,255,0)']],
                                zmin=-1.0,
                                zmax=1.0)
            plot(data=[heatmap],
                layout=_build_layout(title='{} Correlation Heatmap'.format(cor).title()),
                file_name='{}_correlation'.format(cor))
#---------------------------------------------------------------------------------->
    if FLAGS.efficient_frontier or FLAGS.portfolio_weights:
        if not (os.path.exists(PATH_TO_WEIGHTS_FILE)):
            res, comparison = _optimize_weights()
            with open(PATH_TO_WEIGHTS_FILE, "wb") as fp:
                pickle.dump(comparison, fp)
        else:
            with open(PATH_TO_WEIGHTS_FILE, "rb") as fp:
                comparison = pickle.load(fp)
        _plot_efficient_frontier(comparison) if FLAGS.efficient_frontier else _plot_weights_per_asset(comparison)

#---------------------------------------------------------------------------------->
def _build_layout(title, x_axis_title=None, y_axis_title=None, y_axis_type=None):
    """Call plotly.go.Layout
    
    Arguments:
        title {[str]} -- [Title of the graph]
    
    Keyword Arguments:
        x_axis_title {[type]} -- [description] (default: {None})
        y_axis_title {[type]} -- [description] (default: {None})
        y_axis_type {[type]} -- [description] (default: {None})
    
    Returns:
        [Class Layout()] -- [Plotly layout object]

        >>> go.Layout()
        >>> Layout()
        >>> type(go.Layout())
        >>> <class 'plotly.graph_objs._layout.Layout'> 
    """
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
    for i, coin in enumerate(PORTFOLIO_SYMBOLS):
        df = pd.read_csv(PATH_TO_COIN_FILE[i])
        trace = go.Scatter(x=df.Date,
                           y=df['coinmarketcap.coin_btc.price_btc'].pct_change()*100 if pct_change else df['coinmarketcap.coin_btc.price_btc'],
                           name = str(coin).upper())
        data.append(trace)
    return data
#---------------------------------------------------------------------------------->

def make_prophecy(changepoint_prior_scale, column_to_prophet, periods, y_name):
    df_prophet = fbprophet.Prophet(changepoint_prior_scale=changepoint_prior_scale)
    df_prophet.fit(column_to_prophet)
    # df_prophet.fit(df_dollar[['ds', 'y']])
    df_forecast = df_prophet.make_future_dataframe(periods=periods)
    df_forecast = df_prophet.predict(df_forecast)
    y = go.Scatter(x=column_to_prophet['ds'],
                    y=column_to_prophet['y'],
                    name=y_name+str(changepoint_prior_scale),
                    line=dict(color='#94B7F5'))
    yhat = go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='{} yhat {}'.format(y_name, str(changepoint_prior_scale)))
    yhat_upper = go.Scatter(x=df_forecast['ds'],
                    y=df_forecast['yhat_upper'],
                    fill='tonexty',
                    mode='none',
                    name='{} yhat_upper {}'.format(y_name, str(changepoint_prior_scale)),
                    fillcolor='rgba(0,201,253,.21)')
    yhat_lower = go.Scatter(x=df_forecast['ds'],
                    y=df_forecast['yhat_lower'],
                    fill='tonexty',
                    mode='none',
                    name='{} yhat_lower {}'.format(y_name, str(changepoint_prior_scale)),
                    fillcolor='rgba(252,201,5,.05)')
    return y,yhat, yhat_upper, yhat_lower
#---------------------------------------------------------------------------------->



def _build_correlation_df(pct_change=False):
    if not pct_change:
        if not (os.path.exists(PATH_TO_CORRELATION_FILE)):
            base_df = pd.read_csv(PATH_TO_COIN_FILE[0])
            base_df = base_df[['Date','Price $']]

            for i, coin in enumerate(PORTFOLIO_SYMBOLS):
                df = pd.read_csv(PATH_TO_COIN_FILE[i])
                base_df[coin.upper() + '_BTC'] = df['Price BTC']
                base_df[coin.upper() + '_$'] = df['Price $']
            base_df.set_index('Date', inplace=True)
            base_df.drop('Price $', 1, inplace=True)
            base_df.to_csv(PATH_TO_CORRELATION_FILE)
        else:
            base_df = pd.read_csv(PATH_TO_CORRELATION_FILE)
            base_df.set_index('Date', inplace=True)
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
            df = df.set_index('Date')
        return df 
#---------------------------------------------------------------------------------->

def calc_exp_returns(avg_return, weigths):
    """[summary]
    
    Arguments:
        avg_return {[type]} -- [description]
        weigths {[type]} -- [description]
    
    Returns:
        [type] -- [description]
    """
    exp_returns = avg_return.dot(weigths.T)
    return exp_returns
#---------------------------------------------------------------------------------->

def var_cov_matrix(df, weigths):
    """[summary]
    
    Arguments:
        df {[type]} -- [description]
        weigths {[type]} -- [description]
    
    Returns:
        [type] -- [description]
    """

    sigma = np.cov(np.array(df).T, ddof=0) # covariance
    var = (np.array(weigths) * sigma * np.array(weigths).T).sum()
    return var
#---------------------------------------------------------------------------------->

def _optimize_weights():
    """[https://docs.scipy.org/doc/scipy-0.13.0/reference/generated/scipy.optimize.minimize.html]
    
    Returns:
        [type] -- [description]
    """
    df = _build_correlation_df(pct_change=True)
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
    return res, results_comparison_dict
#---------------------------------------------------------------------------------->

def _plot_efficient_frontier(comparison):
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
def _plot_weights_per_asset(comparisson):
    keys = sorted(list(comparisson.keys()))
    index = 0
    df = pd.read_csv(PATH_TO_PCT_CORRELATION_FILE)
    x_itemns = list(df.columns)
    x_itemns.remove('Date')

    fig = tools.make_subplots(rows=4, cols=4, subplot_titles=(keys))
    for i in range(1,5):
        for j in range(1,5):
            trace = go.Bar(x=x_itemns, y=comparisson[keys[index]][1], name='{} %'.format(keys[index]))
            fig.add_trace(trace, row=i, col=j)
            index += 1
    fig['layout'].update(title='Weights per asset at different expected returns (%)',
                         font=dict(color='rgb(255, 255, 255)', size=14),
                         paper_bgcolor='#2d2929',
                         plot_bgcolor='#2d2929')
    offline.plot(fig, filename='docs/weights.html')
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
                 filename='docs/' + file_name + '.html')
#---------------------------------------------------------------------------------->

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='\nDeep analysis of cryptocurrencies')
    parser.add_argument('--efficient_frontier', action='store_true', help='Plot portfolio efficient frontier')
    parser.add_argument('--portfolio_weights', action='store_true', help='Plot portfolio efficient frontier')
    parser.add_argument('--portfolio_change', action='store_true', help='Plot portfolio percent change')
    parser.add_argument('--correlation', action='store_true', help='Plot correlation heatmap')
    parser.add_argument('--plot_coin', type=str, help='Choose coin to plot')
    FLAGS = parser.parse_args()
    import hypeindx
    import pandas as pd
    import numpy as np
    from configs.vars import *
    # from configs.functions import print_dollar
    import plotly.graph_objs as go
    import plotly.offline as offline
    import fbprophet
    import os
    import matplotlib.pyplot as plt
    from scipy.optimize import minimize
    import ad 
    from plotly import tools
    import pickle
    main()
    # print_dollar()