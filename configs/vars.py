import datetime, os
#------------------------------------------------------------->
# coins = ['steem']
# coins = ['bitcoin']
coins= ['bitcoin','ethereum-classic', 'binancecoin', 'litecoin', 'ethereum', 'bitshares', 'steem','dash','nano','zcash','eos','neo','blocknet']
days = '7'
currency = 'usd'
batch_size = 32

wallet = 100
fees = 0.02
gamma = 0.95
epsilon = 1.0
epsilon_min = 0.01
epsilon_decay = 0.995
#------------------------------------------------------------->
keys = ['prices', 'total_volumes', 'market_caps'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
#------------------------------------------------------------->
