import datetime, os
#---------------------------------------------------------------------------------->
####### PORTFOLIO: #########
PORTFOLIO_SYMBOLS = [
    # 'btc',
    'eth',
    'xrp',
    'ltc'
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
    # price in different currencies
    'Price $',
    'Price BTC',
    'Price BNB',
    'Price EOS',
    'Price XRP'
]
FIELDS_PLOT_2 = [
    # social index
    'Price +/- 24h $',
    'Telegram Hype +/- 24h',
    'Usage index by DataLight',
    'Metcalf usage',
    'Telegram Hype',
    'Telegram Mood (average value by one message)',
    'Telegram Mood (total value for all messages)',
    'Twitter Hype 24h',
    'Wikipedia views 30d'
]
FIELDS_PLOT_3 = [
    # market cap index
    'Available Supply', # ??
    'Market Cap',
    'Sending addresses count 24h',
    'Max value of tx. 24h',
    'Receiving addresses count 24h',
    'Tx. count 24h',
    'Tx. sum 24h',
    'Avg. value of tx. 24h $',
    'Max value of tx. in $ 24h',
    'Avg. value of tx. 24h',
    'Tx. sum in $ 24h'
]
FIELDS_PLOT_4 = [
    # momentum index
    'Price +/- 1h $',
    'Price +/-  1h BTC',
    'Price +/- 24h $',
    'Price +/- BTC',
    'Price +/- 7d $',
    'Price +/- 7d  BTC',
    'Liquidity',
    'CVIX 30d',
    'Sharpe Ratio 30d',
    'NVT Ratio',
    'Buy market 24h'
]
FIELDS_PLOT_5 = [
    # volume
    'Volume 24h $',
    'CMO_USD',
    'SMA_USD',
    'MOM_USD'
    'macdsignal_USD',
    'macdhist_USD',
    'macd_USD'
]
FIELDS_PLOT_6 = [
    # market cap per ...
    'Marketcap / Telegram hype',
    'Marketcap / Twitter hype',
    'Marketcap / Usage index by DataLight',

]

STR_PORTFOLIO_SYMBOLS = ','.join(PORTFOLIO_SYMBOLS)
n_features = 3 # price, caps, vol
keys = ['prices', 'market_caps', 'total_volumes'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
# PATH_TO_CORRELATION_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_correlation_' + str(days) + '_' + currency + '.csv'
# PATH_TO_WEIGHTS_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_weighs_' + str(days) + '_' + currency + '.csv'
# PATH_TO_PCT_CORRELATION_FILE = 'datasets/' + str(todays_day) + '-' + str(todays_month) + '_pct_correlation_' + str(days) + '_' + currency + '.csv'
PATH_TO_COIN_FILE = ['datasets/' + symbol.upper() + '_' + TIME_INTERVAL + '_' + FROM_DATE + '_' + TO_DATE + '.csv' for symbol in PORTFOLIO_SYMBOLS]