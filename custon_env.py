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

import ray
from ray.tune import run_experiments, grid_search
from ray.tune.registry import register_env

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
# para criar uma dataframe com as linhas normalizadas e 
# evitar normalizar a cada step, pode usar essa função:
# https://stackoverflow.com/questions/50421196/apply-a-function-to-each-row-of-the-dataframe 
# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.apply.html

class SimpleCorridor(gym.Env):
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
        self.wallet_btc = 0.1
        self.wallet_eth = 0.0
        self.action_space = Discrete(3)
        self.observation_space = Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max, shape=(self.df_rows-2, ), dtype=np.float32) # shape=(number of columns,)

    def reset(self):
        self.index = 0
        row = self.df.iloc[self.index][2:]
        return list(row) # return a row withou the 2 fist columns (date and coin name)

    def step(self, action):
        assert action in [0, 1, 2], action
        price_btc = self.df.iloc[self.index][13]
        actual_wallet_btc = self.wallet_btc
        actual_wallet_eth = self.wallet_eth
        if action == 0: # buy
            actual_wallet_btc -= price_btc
            actual_wallet_eth += price_btc
        elif action == 1: # sell
            actual_wallet_eth -= price_btc
            actual_wallet_btc += price_btc
        
        reward = self.wallet_btc - actual_wallet_btc
        self.index += 1        
        done = self.wallet_btc <= 0.0 or self.index >= self.df_columns-1 # number of rows
        row = self.df.iloc[self.index][2:]
        return list(row), reward, done, {}


if __name__ == "__main__":
    # Can also register the env creator function explicitly with:
    # register_env("corridor", lambda config: SimpleCorridor(config))
    ray.init()
    run_experiments({
        "XRP_demo": {
            "run": "PPO",
            "env": SimpleCorridor,  # or "corridor" if registered above
            "stop": {
                "timesteps_total": 10000,
            },
            "config": {
                "lr": grid_search([1e-2, 1e-4, 1e-6]),  # try different lrs
                "num_workers": 1,  # parallelism
                "env_config": {
                    "corridor_length": 10,
                    "df": pd.read_csv('datasets/XRP_1d_2018-11-01_2019-03-18.csv')
                },
            },
        },
    })