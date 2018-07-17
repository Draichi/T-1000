import warnings, argparse
from datetime import datetime
#------------------------------------------------------------->
warnings.filterwarnings("ignore", category=DeprecationWarning)
#------------------------------------------------------------->
parser = argparse.ArgumentParser(description='Deep analysis of cryptocurrencies')
parser.add_argument('-d', '--days', type=int, default=0, help='7')
parser.add_argument('-c', '--change', type=float, default=0, help='0.02')
parser.add_argument('-$', '--coin', type=str, default=0, help='BTC')
parser.add_argument('-dd', '--title', type=str, default=0, help='BTC')
parser.add_argument('--year', type=int, choices=range(2015, 2018), default=2018)
parser.add_argument('--separate_y_axis', action='store_true')
args = parser.parse_args()
#------------------------------------------------------------->
exchanges = ['COINBASE', 'BITSTAMP', 'ITBIT', 'KRAKEN']
base_url = 'https://poloniex.com/public?command=returnChartData&currencyPair={}&start={}&end={}&period={}'
start_date = datetime.strptime('2015-01-01', '%Y-%m-%d')
end_date = datetime.now()
period = 86400 # daily, 86400 sec/day
altcoins = ['ETH', 'LTC', 'DASH', 'XRP', 'ETC', 'SC', 'XMR', 'XEM']
#------------------------------------------------------------->
HOW_MANY_DAYS      = args.days
title              = args.title
year               = args.year
separate_y_axis    = args.separate_y_axis
REQUIREMENT        = args.change
DATABASE           = 'datasets/altcoins_joined_closes_20181405.csv'
COIN               = args.coin
DATABASE_INDEX_COL = 0
