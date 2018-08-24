import datetime, os
#------------------------------------------------------------->
# coins = ['ethereum-classic']
# coins= ['binancecoin','giant','steem','ethereum-classic']
coins = ['bitcoin', 'ethereum']
days = 60
currency = 'usd'
batch_size = 64
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
#------------------------------------------------------------->
