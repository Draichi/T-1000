import datetime, os
#------------------------------------------------------------->
# customize these: 
coins = ['ethereum-classic', 'qtum']
# coins= ['ethereum', 'giant']
# coins = ['bitcoin']
days = 6
currency = 'btc'
changepoint_prior_scale = 0.09 # 0.01 ~ 0.9
forecast_days = 2
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps'] # if change that, will have to change the getDataVec in function.py
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
batch_size = 32

#------------------------------------------------------------->
