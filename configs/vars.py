import datetime
import os
import numpy as np
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
PRICE_GROUP_1 = [
    'Price $',
    # 'SMA_USD',
    'Price EOS',
    'Price XRP'
]
PRICE_GROUP_2= [
    'Price BTC',
    # 'Marketcap / Twitter hype',

]
PRICE_CHANGE_24 = [
    'Price +/- 24h $',
    'Price +/- BTC'
]
PRICE_CHANGE_1D = [
    'Price +/- 1h $',
    'Price +/-  1h BTC',
]
PRICE_CHANGE_7D = [
    'Price +/- 7d $',
    'Price +/- 7d  BTC',
]
MOMENTUM_IND = [
    'CMO_USD'
]
MACD = [
    'macdsignal_USD',
    'macdhist_USD',
    'macd_USD'
]
HYPE_GROUP_1 = [
    'Telegram Hype +/- 24h',
    'Usage index by DataLight',
    'Metcalf usage',
    'Telegram Hype',
    'Telegram Mood (average value by one message)',
    'Telegram Mood (total value for all messages)',
    'Twitter Hype 24h',
    'Wikipedia views 30d',
    'Marketcap / Telegram hype',
    'Marketcap / Twitter hype',
    'Marketcap / Usage index by DataLight',
]
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
TODAYS_MONTH = datetime.datetime.now().month
TODAYS_DAY = datetime.datetime.now().day
TERMINAL_WIDTH = os.get_terminal_size().columns

# x2 because we need each asset in BTC and $
weigths = np.random.dirichlet(alpha=np.ones(len(PORTFOLIO_SYMBOLS*2)), size=1) # makes sure that weights sums upto 1.
EXP_RETURN_CONSTRAINT = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
BOUNDS = ((0.0, 1.),) * len(PORTFOLIO_SYMBOLS*2) # bounds of the problem

PATH_TO_CORRELATION_FILE = 'datasets/correlation_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
PATH_TO_PCT_CORRELATION_FILE = 'datasets/pct_correlation_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
PATH_TO_WEIGHTS_FILE = 'datasets/weights_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
PATH_TO_COIN_FILE = ['datasets/' + symbol.upper() + '_' + TIME_INTERVAL + '_' + FROM_DATE + '_' + TO_DATE + '.csv' for symbol in PORTFOLIO_SYMBOLS]