"""Plot portfolio

Plot diffrent portfolio informations

Run:
    python plot_portfolio.py --help
"""

import pandas as pd
from configs.vars import coins, days, todays_day, todays_month, currency
import plotly.graph_objs as go
import plotly.offline as offline
#---------------------------------------------------------------------------------->
def _build_layout(title, y_axis_title, y_axis_type=None):
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
def plot(file_name, pct_change=False, title, y_axis_title, y_axis_type=None):
    """[summary]
    
    Arguments:
        title {[type]} -- [description]
        y_axis_title {[type]} -- [description]
    
    Keyword Arguments:
        pct_change {bool} -- [description] (default: {False})
        y_axis_type {[type]} -- [description] (default: {None})
    
    Returns:
        [type] -- [description]
    """

    plot = offline.plot({'data': _build_data(pct_change),
                         'layout': _build_layout(title, y_axis_title, y_axis_type)},
                         filename='{}-{}_{}-{}.html'.format(file_name,
                                                            todays_day,
                                                            todays_month,
                                                            currency))
    return plot
#---------------------------------------------------------------------------------->
def main():
    if args.change:
        plot(file_name='pct_change',
             pct_change=True,
             title='Portfolio Change in {} Days'.format(days),
             y_axis_title='Change (%)')
#---------------------------------------------------------------------------------->
    if args.linear or args.log:
        plot(file_name='linear' if args.linear else 'log',
             title='Portfolio in {} Days'.format(days),
             y_axis_title='Price ({})'.format(currency.upper()),
             y_axis_type='linear' if args.linear else 'log')

#---------------------------------------------------------------------------------->

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
    parser.add_argument('--correlation', action='store_true', help='plot correlation')
    parser.add_argument('--change', action='store_true', help='plot percent change')
    parser.add_argument('--linear', action='store_true', help='plot linear graph')
    parser.add_argument('--log', action='store_true', help='plot log graph')
    args = parser.parse_args()
    main()