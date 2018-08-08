import warnings, argparse
import datetime
#------------------------------------------------------------->
warnings.filterwarnings("ignore", category=DeprecationWarning)
#------------------------------------------------------------->
# coins = [
#     'steem','nano','binancecoin','bitshares','rupaya',
#     'fantasy-gold', 'giant', 'steem-dollars'
# ]
coins = ['binancecoin']
days = 8
keys = ['prices']
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
#------------------------------------------------------------->
parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
parser.add_argument('-d', '--forecast_days', type=int, default=0, help='7')
parser.add_argument('-c', '--change', type=float, default=0, help='0.02')
parser.add_argument('--coin', type=str, default=0, help='BTC')
parser.add_argument('-dd', '--title', type=str, default=0, help='BTC')
parser.add_argument('--year', type=int, choices=range(2015, 2018), default=2018)
parser.add_argument('--separate_y_axis', action='store_true')
args = parser.parse_args()
#------------------------------------------------------------->
forecast_days     = args.forecast_days
requirement        = args.change
DATABASE           = 'datasets/df_joined-{}-{}_{}-days.csv'.format(todays_day, todays_month, days)
coin               = args.coin
DATABASE_INDEX_COL = 0
