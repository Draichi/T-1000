import numpy as np 
import pandas as pd
from collections import Counter 
import pickle, warnings
from sklearn import svm, model_selection, neighbors
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from termcolor import cprint
from config import *
import numpy as np
import pandas as pd
from config.variables.prediction import *
#------------------------------------------------------------->
df = pd.read_csv(DATABASE, index_col=DATABASE_INDEX_COL)
tickers = df.columns.values
df.fillna(0, inplace=True)
#------------------------------------------------------------->
def buy_sell_hold(*args):
    cols = [c for c in args]
    
    for col in cols:
        if col > REQUIREMENT:
            return 'BUY'
        if col < -REQUIREMENT:
            return 'SELL'
    return 'HOLD'
#------------------------------------------------------------->
def process_data_for_labels(ticker):
    
    for i in range(1, HOW_MANY_DAYS+1):
        df['{}_{}d'.format(ticker, i)] = (
            (df[ticker].shift(-i) - df[ticker]) / df[ticker]
        )
    
    df.fillna(0, inplace=True)
    return tickers, df
#------------------------------------------------------------->
def extract_featuresets(ticker):
    tickers, df = process_data_for_labels(ticker)
    
    for i in range(1, HOW_MANY_DAYS+1):
        df['{}_target'.format(COIN)] = list(map(
            buy_sell_hold,
            df['{}_{}d'.format(COIN,i)]
        ))

    vals     = df['{}_target'.format(ticker)].values.tolist()
    str_vals = [str(i) for i in vals]
    print_div()
    cprint('~~> Data spread: {}'.format(Counter(str_vals)), 'magenta')

    df.fillna(0, inplace=True)
    df = df.replace([np.inf, -np.inf], np.nan)
    df.dropna(inplace=True)

    df_vals = df[[ticker for ticker in tickers]].pct_change()
    df_vals = df_vals.replace([np.inf, -np.inf], 0)
    df_vals.fillna(0, inplace=True)

    x = df_vals.values
    y = df['{}_target'.format(ticker)].values.tolist()

    return x, y, df
#------------------------------------------------------------->
def train_the_clf(ticker):
    x, y, df = extract_featuresets(ticker)
    x_train, x_test, y_train, y_test = model_selection.train_test_split(
        x,
        y,
        test_size=0.2
    )
    clf = VotingClassifier([
        ('lsvc', svm.LinearSVC()),
        ('knn', neighbors.KNeighborsClassifier()),
        ('rfor', RandomForestClassifier())
    ])
    clf.fit(x_train, y_train)

    confidence  = clf.score(x_test, y_test)
    predictions = clf.predict(x_test)

    cprint(
        '\n~~> Spread prediction: {}'.format(Counter(predictions)),
        'magenta'
    )
    cprint(
        '\n~~> Accuracy: {0:.3f} %'.format(confidence*100), 
        'magenta'
    )
    print_div()
    
    return confidence
#------------------------------------------------------------->
def print_div():
    cprint('~'*70, 'cyan')
#------------------------------------------------------------->
def get_quandl_data(quandl_id):
    path = '{}.pkl'.format(quandl_id).replace('/','-')
    cache_path = 'datasets/' + path
    try:
        f = open(cache_path, 'rb')
        df = pickle.load(f)
        print('-- loaded {} from cache'.format(quandl_id))
    except (OSError, IOError) as e:
        print('-- downloading {} from quandl'.format(quandl_id))
        df = quandl.get(quandl_id, returns="pandas")
        df.to_pickle(cache_path)
        print('-- cached {} at {}'.format(quandl_id, cache_path))
    return df
#------------------------------------------------------------->
def merge_dfs_on_column(dataframes, labels, col):
    series_dict = {}
    for index in range(len(dataframes)):
        series_dict[labels[index]] = dataframes[index][col]
    return pd.DataFrame(series_dict)
#------------------------------------------------------------->
def get_json_data(json_url, path):
    # download and cache json data, return as dataframe
    pkl = '{}.pkl'.format(path)
    cache_path = 'datasets/' + pkl
    try:
        f = open(cache_path, 'rb')
        df = pickle.load(f)
        print('-- loaded {} from cache'.format(path))
    except (OSError, IOError) as e:
        print('-- downloading {}'.format(json_url))
        df = pd.read_json(json_url)
        df.to_pickle(cache_path)
        print('-- cached {}'.format(path))
    return df
#------------------------------------------------------------->
def get_crypto_data(poloniex_pair):
    # retrive crypto data from poloniex
    json_url = base_url.format(
        poloniex_pair, 
        start_date.timestamp(), 
        end_date.timestamp(), 
        period
    )
    data_df = get_json_data(json_url, poloniex_pair)
    data_df = data_df.set_index('date')
    return data_df
