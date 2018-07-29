import warnings, argparse
import datetime
#------------------------------------------------------------->
warnings.filterwarnings("ignore", category=DeprecationWarning)
#------------------------------------------------------------->
coins = ['giant','rupaya','zcoin','nano','steem']
days = 7
keys = ['prices']
todays_month = datetime.datetime.now().month
todays_day = datetime.datetime.now().day
#------------------------------------------------------------->
parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
parser.add_argument('-ds', '--dayss', type=int, default=0, help='7')
parser.add_argument('-c', '--change', type=float, default=0, help='0.02')
parser.add_argument('--coin', type=str, default=0, help='BTC')
parser.add_argument('-dd', '--title', type=str, default=0, help='BTC')
parser.add_argument('--year', type=int, choices=range(2015, 2018), default=2018)
parser.add_argument('--separate_y_axis', action='store_true')
args = parser.parse_args()
#------------------------------------------------------------->
# exchanges = ['COINBASE', 'BITSTAMP', 'ITBIT', 'KRAKEN']
# base_url = 'https://poloniex.com/public?command=returnChartData&currencyPair={}&start={}&end={}&period={}'
# start_date = datetime.strptime('2015-01-01', '%Y-%m-%d')
# end_date = datetime.now()
# period = 86400 # daily, 86400 sec/day
# altcoins = ['ETH', 'LTC', 'DASH', 'XRP', 'ETC', 'SC', 'XMR', 'XEM']
# #------------------------------------------------------------->
dayss      = args.dayss
# title              = args.title
# year               = args.year
# separate_y_axis    = args.separate_y_axis
requirement        = args.change
DATABASE           = 'datasets/base_df-29-7.csv'
coin               = args.coin
DATABASE_INDEX_COL = 0
