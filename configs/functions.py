import numpy as np
import pandas as pd
from collections import Counter
from sklearn import svm, model_selection, neighbors
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from termcolor import cprint
from configs.vars import *
#------------------------------------------------------------->
df = pd.read_csv(DATABASE, index_col=DATABASE_INDEX_COL)
tickers = df.columns.values
df.fillna(0, inplace=True)
#------------------------------------------------------------->
def buy_sell_hold(*args):
    cols = [c for c in args]

    for col in cols:
        if col > requirement:
            return 'BUY'
        if col < -requirement:
            return 'SELL'
    return 'HOLD'
#------------------------------------------------------------->
def process_data_for_labels(ticker):
    for i in range(1, forecast_days+1):
        df['{}_{}d'.format(ticker, i)] = (
            (df[ticker].shift(-i) - df[ticker]) / df[ticker]
        )
    df.fillna(0, inplace=True)
    df.to_csv('process_data.csv')
    return tickers, df
#------------------------------------------------------------->
def extract_featuresets(ticker):
    tickers, df = process_data_for_labels(ticker)
    for i in range(1, forecast_days+1):
        df['{}_target'.format(coin)] = list(map(
            buy_sell_hold,
            df['{}_{}d'.format(coin,i)]
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
    df.to_csv('{}-test.csv'.format(coin))
    return x, y, df
#------------------------------------------------------------->
def train_the_clf(ticker):
    x, y, _ = extract_featuresets(ticker)
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