import datetime, os
#------------------------------------------------------------->
coins = ['bitcoin', 'nano', 'ripple']
# coins = ['binancecoin', 'nano', 'ripple']
# coins= ['bitcoin','giant','ethereum-classic', 'binancecoin', 'litecoin', 'ethereum', 'bitshares', 'steem','dash','nano','zcash','eos','neo','blocknet']
days = '30'
currency = 'usd'
batch_size = 512 # 16, 32, 64, 128, 256...

wallet = 8000
n_orders = 350
fees = 1
gamma = 0.95
epsilon = 1.0
epsilon_min = 0.01
epsilon_decay = 0.995
#------------------------------------------------------------->
keys = ['prices', 'market_caps', 'total_volumes'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
#------------------------------------------------------------->
