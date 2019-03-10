"""Plot portfolio

Plot diffrent portfolio informations

Run:
    python plot_portfolio.py --help
"""

import pandas as pd
from configs.vars import coins, days, todays_day, todays_month, currency
import plotly.graph_objs as go
import plotly.offline as offline
import fbprophet
#---------------------------------------------------------------------------------->
def _build_layout(title, y_axis_title, y_axis_type=None):
    """[summary]
    
    Arguments:
        title {[type]} -- [description]
        y_axis_title {[type]} -- [description]
    
    Keyword Arguments:
        y_axis_type {[type]} -- [description] (default: {None})
    
    Returns:
        [type] -- [description]
    """

    layout = go.Layout(plot_bgcolor='#2d2929',
                       paper_bgcolor='#2d2929',
                       title=title,
                       font=dict(color='rgb(255, 255, 255)'),
                       legend=dict(orientation="h"),
                       xaxis=dict(type='date'),
                       yaxis=dict(title=y_axis_title, type=y_axis_type))
    return layout
#---------------------------------------------------------------------------------->
def _build_data(pct_change=False):
    """[summary]
    
    Keyword Arguments:
        pct_change {bool} -- [description] (default: {False})
    
    Returns:
        [type] -- [description]
    """

    data = []
    for coin in coins:
        df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day,
                                                                todays_month,
                                                                coin,
                                                                days,
                                                                currency))
        trace = go.Scatter(x=df.date,
                           y=df['prices'].pct_change()*100 if pct_change else df['prices'],
                           name = str(coin).upper())
        data.append(trace)
    return data
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
                 filename='{}-{}_{}-{}.html'.format(file_name,
                                                    todays_day,
                                                    todays_month,
                                                    currency))
#---------------------------------------------------------------------------------->
def main():
    """[summary]
    """

    if args.change:
        plot(data=_build_data(pct_change=True),
             layout=_build_layout(title='Portfolio Change in {} Days'.format(days),
                                  y_axis_title='Change (%)'),
             file_name='pct_change',
             pct_change=True)
#---------------------------------------------------------------------------------->
    if args.linear or args.log:
        plot(data=_build_data(),
             layout=_build_layout(title='Portfolio in {} Days'.format(days),
                                  y_axis_title='Price ({})'.format(currency.upper()),
                                  y_axis_type='linear' if args.linear else 'log'),
             file_name='linear' if args.linear else 'log')
#---------------------------------------------------------------------------------->
    if args.forecast_coin and args.forecast_days and args.forecast_scale:
        df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day,todays_month,args.forecast_coin,days,currency))
        df['ds'] = df['date']
        df['y'] = df['prices']
        df = df[['ds', 'y']]
        df_prophet = fbprophet.Prophet(changepoint_prior_scale=args.forecast_scale)
        df_prophet.fit(df)
        df_forecast = df_prophet.make_future_dataframe(periods=int(args.forecast_days))
        df_forecast = df_prophet.predict(df_forecast)
        data = [
            go.Scatter(x=df['ds'], y=df['y'], name='Price', line=dict(color='#94B7F5')),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat'], name='yhat'),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_upper'], fill='tonexty', mode='none', name='yhat_upper', fillcolor='rgba(0,201,253,.21)'),
            go.Scatter(x=df_forecast['ds'], y=df_forecast['yhat_lower'], fill='tonexty', mode='none', name='yhat_lower', fillcolor='rgba(252,201,5,.05)'),
        ]
        plot(data=data,
             layout=_build_layout(title='{} Days of {} Forecast'.format(args.forecast_days, currency.upper()),
                                  y_axis_title='Price ({})'.format(currency.upper())),
             file_name='forecast')
#---------------------------------------------------------------------------------->

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
    parser.add_argument('--correlation', action='store_true', help='plot correlation')
    parser.add_argument('--change', action='store_true', help='plot percent change')
    parser.add_argument('--linear', action='store_true', help='plot linear graph')
    parser.add_argument('--log', action='store_true', help='plot log graph')
    parser.add_argument('--forecast_coin', '-fc', type=str, help='plot forecast graph')
    parser.add_argument('--forecast_days', '-fd', type=int, default=5, help='plot forecast graph')
    parser.add_argument('--forecast_scale', '-fs', type=float, default=0.1, help='plot forecast graph')
    args = parser.parse_args()
    main()