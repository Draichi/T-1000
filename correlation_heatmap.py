import pandas as pd
from configs.vars import coins, days, todays_day, todays_month, currency
import plotly.graph_objs as go
import plotly.offline as offline
# correlation methods: {pearson, kendall, spearman} 
# correlation or covariance?
#---------------------------------------------------------------------------------->
def _get_coin_data(coin):
    df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day,
                                                           todays_month,
                                                           coin,
                                                           days,
                                                           currency))
    return df
#---------------------------------------------------------------------------------->
base_df = _get_coin_data(coins[0])
base_df[coins[0]] = base_df['prices']
base_df = base_df[['date', coins[0]]]
#---------------------------------------------------------------------------------->
for coin in coins[1:]:
    df = _get_coin_data(coin)
    base_df[coin] = df['prices']
#---------------------------------------------------------------------------------->
base_df.set_index('date', inplace=True)
base_df.to_csv('datasets/{}-{}_correlated_d{}_{}.csv'.format(todays_day,
                                                             todays_month,
                                                             days,
                                                             currency))
#---------------------------------------------------------------------------------->
heatmap = go.Heatmap(
    z=base_df.pct_change().corr(method='pearson').values,
    x=base_df.pct_change().columns,
    y=base_df.pct_change().columns,
    colorbar=dict(title='Pearson Coefficient'),
    colorscale=[[0, 'rgb(255,0,0)'], [1, 'rgb(0,255,0)']],
    zmin=-1.0,
    zmax=1.0
)
layout = go.Layout(
    title='Correlation heatmap - {} days'.format(days),
    plot_bgcolor='#2d2929',
    paper_bgcolor='#2d2929',
    font=dict(color='rgb(255, 255, 255)')
)
offline.plot({'data': [heatmap],'layout': layout})