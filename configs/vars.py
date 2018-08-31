import datetime, os
#------------------------------------------------------------->
# coins = ['bitcoin']
coins= ['giant','ethereum-classic']
days = 60
currency = 'btc'
batch_size = 32
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
#------------------------------------------------------------->
