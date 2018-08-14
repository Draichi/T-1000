import datetime, os
#------------------------------------------------------------->
# customize these: 
coins = ['nano', 'binancecoin', 'monero', 'zcash']
days = 90
currency = 'btc'
changepoint_prior_scale = 0.15 # 0.10 ~ 0.50
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps'] # if change that, will have to change the getDataVec in function.py
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
batch_size = 32

#------------------------------------------------------------->
