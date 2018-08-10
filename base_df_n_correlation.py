import pandas as pd
from configs.charts import correlation_heatmap
from configs.vars import coins, days, todays_day, todays_month, currency
#------------------------------------------------------------->
def get_coin_data(coin):
    df = pd.read_csv('datasets/{}-{}_{}_d{}_{}.csv'.format(todays_day, todays_month, coin, days, currency))
    return df
#------------------------------------------------------------->
base_df = get_coin_data(coins[0])
for coin in coins[1:]:
    df = get_coin_data(coin)
    base_df[coin] = df[coin]
#------------------------------------------------------------->
base_df.set_index('date', inplace=True)
base_df.pct_change().corr(method='pearson')
base_df.to_csv('datasets/{}-{}_joined_d{}_{}.csv'.format(todays_day, todays_month, days, currency))
#------------------------------------------------------------->
correlation_heatmap(base_df.pct_change(), '{} from {} days'.format(str(coins), days))