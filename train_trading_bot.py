# https://github.com/ray-project/ray/blob/master/python/ray/rllib/rollout.py
# copiar o arquivo e registrar o custom env aqui

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
import gym
from gym.spaces import Discrete, Box
from sklearn.preprocessing import normalize

import os
from configs.vars import *

# import hypeindx

import ray
from ray.tune import run_experiments, grid_search
# from ray.tune.registry import register_env

def init_data(symbol):
    if not (os.path.exists('datasets/ETH-BTC_trading.csv')):
        df = pd.read_csv('datasets/ETH-BTC.csv')
        # df['Volume 24h $'] = df['Volume 24h $'] * 1e-11
        # df['Wikipedia views 30d'] = df['Wikipedia views 30d'] * 1e-5
        # df['Market Cap'] = df['Market Cap'] * 1e-11
        # df['Price EOS'] = df['Price EOS'] * 1e-3
        # df['Price XRP'] = df['Price XRP'] * 1e-3
        # df['Telegram Mood (total value for all messages)'] = df['Telegram Mood (total value for all messages)'] * 1e-3
        # df['Buy market 24h'] = df['Buy market 24h'] * 1e-3
        df['wallet_btc'] = WALLET_BTC
        df['wallet_symbol'] = 0.0
        df.to_csv('datasets/ETH-BTC_trading.csv')
        df.drop('Date', axis=1, inplace=True)
        df_array = df.values.tolist()
        keys = df.keys()
        ##############################
        # print(keys)
        # print(list(df.iloc[0].values))
        # print(df_array[0])
        # >>> list(df.iloc[0].values) == df_array[0]
        # >>> True
        ##############################
    else:
        df = pd.read_csv('datasets/ETH-BTC_trading.csv')
        df.drop('Date', axis=1, inplace=True)
        df_array = df.values.tolist()
        keys = df.keys()
    return keys, df_array


class TradingEnv(gym.Env):
    def __init__(self, config):
        # self.keys, self.symbol_list = init_data(FLAGS.symbol)
        self.keys = config['keys']
        self.symbol_list = config['symbols']
        self.index = 0
        self.dicount_rate = 1 - FEES
        self.wallet_btc = WALLET_BTC
        self.wallet_symbol = 0.0
        self.action_space = Discrete(3)
        self.observation_space = Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max,
            shape=(len(self.keys), ), dtype=np.float32
        )
            # low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max, shape=(self.df_rows-2, ), dtype=np.float32) # shape=(number of columns,)

    def reset(self):
        self.index = 0
        self.wallet_btc = WALLET_BTC
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

        price_btc_index = list(self.keys).index('close')
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

    def render(self, savefig=False, filename='myfig'):
        if self._first_render:
            self._f, self._ax = plt.subplots(
                len(self._spread_coefficients) + int(len(self._spread_coefficients) > 1),
                sharex=True
            )
            if len(self._spread_coefficients) == 1:
                self._ax = [self._ax]
            self._f.set_size_inches(12, 6)
            self._first_render = False
            self._f.canvas.mpl_connect('close_event', self._handle_close)
        if len(self._spread_coefficients) > 1:
            # TODO: To be checked
            for prod_i in range(len(self._spread_coefficients)):
                bid = self._prices_history[-1][2 * prod_i]
                ask = self._prices_history[-1][2 * prod_i + 1]
                self._ax[prod_i].plot([self.index, self.index + 1],
                                      [bid, bid], color='white')
                self._ax[prod_i].plot([self.index, self.index + 1],
                                      [ask, ask], color='white')
                self._ax[prod_i].set_title('Product {} (spread coef {})'.format(
                    prod_i, str(self._spread_coefficients[prod_i])))

        price_btc_index = list(self.keys).index('Price BTC')
        observable_state = self.symbol_list[self.index]
        price_btc_before_action = observable_state[price_btc_index]
        # Spread price
        prices = price_btc_before_action
        # bid, ask = calc_spread(prices, self._spread_coefficients)
        self._ax[-1].plot([self.index, self.index + 1],
                          [prices, prices], color='white')
        # self._ax[-1].plot([self.index, self.index + 1],
        #                   [prices, prices], color='white')
        ymin, ymax = self._ax[-1].get_ylim()
        yrange = ymax - ymin
        if self.action == 1: #sell
            self._ax[-1].scatter(self.index + 0.5, prices + 0.03 *
                                 yrange, color='orangered', marker='v')
        elif self.action == 0: #buy
            self._ax[-1].scatter(self.index + 0.5, prices - 0.03 *
                                 yrange, color='lawngreen', marker='^')
        # plt.suptitle('Cumulated Reward: ' + "%.2f" % self._total_reward + ' ~ ' +
        #              'Cumulated PnL: ' + "%.2f" % self._total_pnl + ' ~ ' +
        #              'Position: ' + ['flat', 'long', 'short'][list(self._position).index(1)] + ' ~ ' +
        #              'Entry Price: ' + "%.2f" % self._entry_price)
        self._f.tight_layout()
        plt.xticks(range(self.index)[::5])
        plt.xlim([max(0, self.index - 80.5), self.index + 0.5])
        plt.subplots_adjust(top=0.85)
        plt.pause(0.01)
        if savefig:
            plt.savefig(filename)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='\n')
    parser.add_argument('--symbol', type=str, help='Choose coin to train')
    parser.add_argument('--algo', type=str, help='Choose algorithm to train')
    FLAGS = parser.parse_args()
    keys, symbols = init_data(FLAGS.symbol)
    # Can also register the env creator function explicitly with:
    # register_env("corridor", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "{}_{}_{}_{}".format(FLAGS.symbol.upper(),TIME_INTERVAL,FROM_DATE,TO_DATE): {
            "run": FLAGS.algo,
            "env": TradingEnv,  # or "corridor" if registered above
            "stop": {
                "timesteps_total": 1e6,
            },
            "config": {
                "lr": grid_search([
                    # 1e-2,
                    # 1e-4,
                    # 1e-5,
                    # 1e-6,
                    1e-7
                ]),
                "num_workers": 2,  # parallelism
                'observation_filter': 'MeanStdFilter',
                "env_config": {
                    'keys': keys,
                    'symbols': symbols
                },
            }
        }
    })