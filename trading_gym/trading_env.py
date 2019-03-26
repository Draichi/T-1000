"""
Classic cart-pole system implemented by Rich Sutton et al.
Copied from http://incompleteideas.net/sutton/book/code/pole.c
permalink: https://perma.cc/C9ZM-652R
"""

import numpy as np
import pandas as pd
import gym
from gym.spaces import Discrete, Box

def init_data():
    df = pd.read_csv('/home/lucas/Documents/cryptocurrency_prediction/datasets/LTC_1d_2018-11-01_2019-03-18.csv')
    df['Volume 24h $'] = df['Volume 24h $'] * 1e-11
    df['Wikipedia views 30d'] = df['Wikipedia views 30d'] * 1e-5
    df['Market Cap'] = df['Market Cap'] * 1e-11
    df['Price EOS'] = df['Price EOS'] * 1e-3
    df['Price XRP'] = df['Price XRP'] * 1e-3
    df['Telegram Mood (total value for all messages)'] = df['Telegram Mood (total value for all messages)'] * 1e-3
    df['Buy market 24h'] = df['Buy market 24h'] * 1e-3
    df['wallet_btc'] = 1.0
    df['wallet_symbol'] = 0.0
    # df.to_csv('datasets/trading_{}_{}_{}_{}.csv'.format(symbol.upper(), TIME_INTERVAL, FROM_DATE, TO_DATE))
    df.drop(['Date', 'Coin'], axis=1, inplace=True)
    df_array = df.values.tolist()
    keys = df.keys()

    return keys, df_array

class TradingEnv(gym.Env):
    """Example of a custom env in which you have to walk down a corridor.

     Observation:
        Type: Box(4)
        Num	Observation                 Min         Max
        0	open price                -4.8            4.8
        1	close price               -Inf            Inf
        2	Momentum                  -24 deg        24 deg
        3	Volume                    -Inf            Inf
    Actions:
        Type: Discrete(3)
        Num	Action
        0	Buy
        1	Sell
        2   Hold
        TODO
        - buy or sell a proportion of the avaiable on wallet (20%, 30%...)

     Reward:
        Reward is the natural log of the wallet difference between before action and after action
    """

    def __init__(self):
        # self.keys, self.symbol_list = init_data(FLAGS.symbol)
        self.keys, self.symbol_list = init_data()
        self.index = 0
        self.dicount_rate = 0.999 # works like the tx
        self.wallet_btc = 1.0
        self.wallet_symbol = 0.0
        self.action_space = Discrete(3)
        self.observation_space = Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max,
            shape=(len(self.keys), ), dtype=np.float32
        )
            # low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max, shape=(self.df_rows-2, ), dtype=np.float32) # shape=(number of columns,)

    def reset(self):
        self.index = 0
        self.wallet_btc = 1.0
        self.wallet_symbol = 0.0
        state = self.symbol_list[self.index]
        # print('state')
        # print(state)
        # normalized_state = normalize(state[:,np.newaxis], axis=0).ravel()
        # return normalized_state
        return state

    def step(self, action):
        if action not in [0,1,2]:
            raise AssertionError()

        price_btc_index = list(self.keys).index('Price BTC')
        wallet_btc_index = list(self.keys).index('wallet_btc')
        wallet_symbol_index = list(self.keys).index('wallet_symbol')
        observable_state = self.symbol_list[self.index]
        price_btc_before_action = observable_state[price_btc_index]

        total_portfolio_value_before_action = self.wallet_btc * price_btc_before_action

        if action == 0: # buy
            self.wallet_btc -= price_btc_before_action
            self.wallet_symbol += price_btc_before_action
        elif action == 1: # sell
            self.wallet_btc += price_btc_before_action
            self.wallet_symbol -= price_btc_before_action


        price_btc_after_action = observable_state[price_btc_index]

        total_portfolio_value_after_action = self.dicount_rate * (self.wallet_btc * price_btc_after_action)

        reward = total_portfolio_value_after_action - total_portfolio_value_before_action

        self.index += 1
        next_observable_state = self.symbol_list[self.index]

        next_observable_state[wallet_btc_index] = self.wallet_btc
        next_observable_state[wallet_symbol_index] = self.wallet_symbol

        # normalized_next_state = normalize(next_observable_state[:,np.newaxis], axis=0).ravel()

        done = self.wallet_btc < 0.0 or self.index >= len(self.symbol_list)-1

        # return normalized_next_state, reward, done, {}
        return next_observable_state, reward, done, {}