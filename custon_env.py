"""Example of a custom gym environment. Run this for a demo.

This example shows:
  - using a custom environment
  - using Tune for grid search

You can visualize experiment results in ~/ray_results using TensorBoard.


this file need env ray to run

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
import gym
from gym.spaces import Discrete, Box
from sklearn.preprocessing import normalize


import ray
from ray.tune import run_experiments, grid_search
# from ray.tune.registry import register_env

# TODO
# learn more abou Box()
# how use it on my abservation space
#
# nesta pasta puxar o read_csv com a df certinha, e
# implementar no step o que está hj no functions.py
#
# pra calcular o reward, ter em mente que o objetivo
# é aumentar o valor da carteira, e para isso, todos
# os assets comprados tem que ter o preço convertido
# para a moeda e em seguida somados com o restante
# da carteira, o log da diferença entre carteira antes
# e depois da ação é o reward
#
# transformar o df em uma list, fazer slice uma dataframe consome
# muita memoria
#
# para criar uma dataframe com as linhas normalizadas e
# evitar normalizar a cada step, pode usar essa função:
# https://stackoverflow.com/questions/50421196/apply-a-function-to-each-row-of-the-dataframe
# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.apply.html

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

    def __init__(self, config):
        # self.df = pd.read_csv('datasets/XRP_1d_2018-11-01_2019-03-18.csv')
        self.df = config['df']
        # print('self.df.shape[1]')
        # print(self.df.shape[1])
        # self.end_pos = config["corridor_length"]
        self.df_columns, self.df_rows = self.df.shape
        # self.cur_pos = 0
        self.index = 0
        self.dicount_rate = 0.99 # works like the tx
        self.wallet_btc = 0.1
        self.wallet_eth = 0.0
        self.action_space = Discrete(3)
        self.observation_space = Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max, shape=(self.df_rows-2, ), dtype=np.float32) # shape=(number of columns,)

    def reset(self):
        self.index = 0
        self.wallet_btc = 0.1
        self.wallet_eth = 0.0
        row = np.array(self.df.iloc[self.index][2:])
        normalized_row = normalize(row[:,np.newaxis], axis=0).ravel()
        return normalized_row # return a row withou the 2 fist columns (date and coin name)

    def step(self, action):
        if action not in [0,1,2]:
            raise AssertionError()
                # _, _, tb = sys.exc_info()
                # traceback.print_tb(tb) # Fixed format
                # tb_info = traceback.extract_tb(tb)
                # filename, line, func, text = tb_info[-1]

                # print('An error occurred on line {} in statement {}'.format(line, text))
                # exit(1)

        # row = self.df.iloc[self.index][2:] # unnused
        price_btc_before_action = self.df.iloc[self.index][13]
        wallet_btc_before_action = self.wallet_btc
        wallet_btc_after_action = self.wallet_btc
        # wallet_eth_before_action = self.wallet_eth
        wallet_eth_after_action = self.wallet_eth
        total_portfolio_value_before_action = wallet_btc_before_action * price_btc_before_action

        if action == 0: # buy
            # TODO
            # manage wallets
            # add tx
            # add porfolio value on next_row list
            wallet_btc_after_action -= price_btc_before_action
            wallet_eth_after_action += price_btc_before_action
        elif action == 1: # sell
            wallet_eth_after_action -= price_btc_before_action
            wallet_btc_after_action += price_btc_before_action

        self.index += 1

        price_btc_after_action = self.df.iloc[self.index][13]
        total_portfolio_value_after_action = self.dicount_rate * (wallet_btc_after_action * price_btc_after_action)

        reward = total_portfolio_value_after_action - total_portfolio_value_before_action
        next_row = np.array(self.df.iloc[self.index][2:])
        normalized_next_row = normalize(next_row[:,np.newaxis], axis=0).ravel()
        done = self.wallet_btc <= 0.0 or self.index >= self.df_columns-1 # number of rows
        return normalized_next_row, reward, done, {}


if __name__ == "__main__":
    # Can also register the env creator function explicitly with:
    # register_env("corridor", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "XRP_demo": {
            "run": "PPO",
            "env": TradingEnv,  # or "corridor" if registered above
            "stop": {
                "timesteps_total": 100000,
            },
            "config": {
                "lr": grid_search([1e-2, 1e-4, 1e-6]),  # try different lrs
                "num_workers": 1,  # parallelism
                # 'observation_filter': 'MeanStdFilter',
                "env_config": {
                    "df": pd.read_csv('datasets/XRP_1d_2018-11-01_2019-03-18.csv')
                },
            },
        },
    })