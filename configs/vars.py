import warnings, argparse
import datetime, numpy
#------------------------------------------------------------->
warnings.filterwarnings("ignore", category=DeprecationWarning)
numpy.warnings.filterwarnings('ignore')
#------------------------------------------------------------->
coins = ['giant','steem', 'nano', 'binancecoin', 'neo', 'bitshares',]
# coins = ['zcoin']
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
dayss      = args.dayss
requirement        = args.change
DATABASE           = 'datasets/base_df-29-7.csv'
coin               = args.coin
DATABASE_INDEX_COL = 0
