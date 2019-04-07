import datetime
import os
import numpy as np
#---------------------------------------------------------------------------------->
####### PORTFOLIO: #########
# PORTFOLIO_SYMBOLS = [
#     # 'btc',
#     'eth',
#     'xrp',
#     'ltc'
# ]
TIME_INTERVAL = '1d'
FROM_DATE = '2018-11-01'
TO_DATE = '2019-03-18'
#---------------------------------------------------------------------------------->
####### MARKET PARAMETERS: #########
WALLET_BTC = 1.0
n_orders = 500
FEES = 0.002 # 0.2%
#---------------------------------------------------------------------------------->
TODAYS_MONTH = datetime.datetime.now().month
TODAYS_DAY = datetime.datetime.now().day

# # x2 because we need each asset in BTC and $
# weigths = np.random.dirichlet(alpha=np.ones(len(PORTFOLIO_SYMBOLS*2)), size=1) # makes sure that weights sums upto 1.
# EXP_RETURN_CONSTRAINT = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
# BOUNDS = ((0.0, 1.),) * len(PORTFOLIO_SYMBOLS*2) # bounds of the problem

# PATH_TO_CORRELATION_FILE = 'datasets/correlation_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
# PATH_TO_PCT_CORRELATION_FILE = 'datasets/pct_correlation_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
# PATH_TO_WEIGHTS_FILE = 'datasets/weights_' + TIME_INTERVAL + '_' + FROM_DATE + TO_DATE + '.csv'
# PATH_TO_COIN_FILE = ['datasets/' + symbol.upper() + '_' + TIME_INTERVAL + '_' + FROM_DATE + '_' + TO_DATE + '.csv' for symbol in PORTFOLIO_SYMBOLS]