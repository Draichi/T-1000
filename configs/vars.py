import datetime, os
#---------------------------------------------------------------------------------->
####### PORTFOLIO: #########
PORTFOLIO_SYMBOLS = [
    # 'btc',
    'eth',
    'eos',
    'ada'
]

# https://api.datalight.me/v1/object/
FIELDS = [ 
    'coinmarketcap.coin_btc.price_btc',
    'telegram.coin_hype_mood_daily.mood',
    'twitter.hype.twitter_hype',
    'ethereum_go.transaction_stat_usd_24h.dl_block_ind',
    'ethereum_go.transaction_calc.trxns_sum',
    'current.coin.rate_yearly',
    'ethereum_go.transaction_calc.trxns_count',
    'coinmarketcap.coin_cvix_30d_1h.cvix',
    'coinmarketcap.coin_calc.liquidity',
    'coinmarketcap.coin.price_usd'
]
TIME_INTERVAL = '1d'
FROM_DATE = '2018-11-01'
TO_DATE = '2019-01-04'
#---------------------------------------------------------------------------------->
####### MARKET PARAMETERS: #########
wallet = 3000.00
n_orders = 500
fees = 3
#---------------------------------------------------------------------------------->
####### HYPERPARAMETERS: #########
epochs = 1
batch_size = 32 # 4, 8, 16, 32...
gamma = 0.95
epsilon = 0.1
epsilon_min = 0.01
epsilon_decay = 0.995
#---------------------------------------------------------------------------------->
####### CONSTANTS (DO NOT CHANGE) #########
FIELDS_PLOT_1 = [
    'coinmarketcap.coin_btc.price_btc',
    'telegram.coin_hype_mood_daily.mood',
    'ethereum_go.transaction_stat_usd_24h.dl_block_ind',
    'current.coin.rate_yearly',
    'coinmarketcap.coin_cvix_30d_1h.cvix',
    'coinmarketcap.coin_calc.liquidity',
    
]
FIELDS_PLOT_2 = [
    'coinmarketcap.coin.price_usd',
    'ethereum_go.transaction_calc.trxns_count',
    'ethereum_go.transaction_calc.trxns_sum',
    'twitter.hype.twitter_hype',
    'SMA_USD',

]
STR_PORTFOLIO_SYMBOLS = ','.join(PORTFOLIO_SYMBOLS)
STR_FIELDS = ','.join(FIELDS)
n_features = 3 # price, caps, vol
keys = ['prices', 'market_caps', 'total_volumes'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
# PATH_TO_CORRELATION_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_correlation_' + str(days) + '_' + currency + '.csv'
# PATH_TO_WEIGHTS_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_weighs_' + str(days) + '_' + currency + '.csv'
# PATH_TO_PCT_CORRELATION_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_pct_correlation_' + str(days) + '_' + currency + '.csv'
PATH_TO_COIN_FILE = ['datasets/' + symbol.upper() + '_' + TIME_INTERVAL + '_' + FROM_DATE + '_' + TO_DATE + '.csv' for symbol in PORTFOLIO_SYMBOLS]