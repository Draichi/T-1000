import datetime, os
#------------------------------------------------------------->
coins = ['bitcoin', 'nano', 'ripple']
# coins = ['binancecoin', 'nano', 'ripple']
# coins= ['bitcoin','giant','ethereum-classic', 'binancecoin', 'litecoin', 'ethereum', 'bitshares', 'steem','dash','nano','zcash','eos','neo','blocknet']
days = '90'
currency = 'usd'

wallet = 3000.00
n_orders = 500
fees = 3

epochs = 1
batch_size = 64 # 4, 8, 16, 32...
gamma = 0.95
epsilon = 0.1
epsilon_min = 0.01
epsilon_decay = 0.995
#------------------------------------------------------------->
n_features = 3 # price, caps, vol
keys = ['prices', 'market_caps', 'total_volumes'] # if change this, change configs/function.py:22
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
terminal_width = os.get_terminal_size().columns
#------------------------------------------------------------->
