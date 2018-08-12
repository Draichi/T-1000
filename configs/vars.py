import datetime
#------------------------------------------------------------->
# customize these: 
coins = ['bitcoin', 'litecoin']
days = 7
currency = 'usd'
changepoint_prior_scale = 0.15 # 0.10 ~ 0.50
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps']
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
#------------------------------------------------------------->
