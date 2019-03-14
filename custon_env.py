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
        self.true_data, self.normalized_data = get_datasets('ethereum')
        self.end_pos = config["corridor_length"]
        self.cur_pos = 0
        self.action_space = Discrete(2)
        self.observation_space = Box(
            0.0, self.end_pos, shape=(1, ), dtype=np.float32)

    def get_datasets(coin):
        """Return the dataset for a given currency and the normalized one"""
        df = 'PLACEHOLDER'
        nomr_df = 'PLACEHOLDER'
        return df, norm_df

    def reset(self):
        self.cur_pos = 0
        return [self.cur_pos]

    def step(self, action):
        assert action in [0, 1], action
        if action == 0 and self.cur_pos > 0:
            self.cur_pos -= 1
        elif action == 1:
            self.cur_pos += 1
        done = self.cur_pos >= self.end_pos
        return [self.cur_pos], 1 if done else 0, done, {}


if __name__ == "__main__":
    # Can also register the env creator function explicitly with:
    # register_env("corridor", lambda config: SimpleCorridor(config))
    ray.init()
    run_experiments({
        "demo": {
            "run": "IMPALA",
            "env": SimpleCorridor,  # or "corridor" if registered above
            "stop": {
                "timesteps_total": 10000,
            },
            "config": {
                "lr": grid_search([1e-2, 1e-4, 1e-6]),  # try different lrs
                "num_workers": 1,  # parallelism
                "env_config": {
                    "corridor_length": 10,
                },
            },
        },
    })