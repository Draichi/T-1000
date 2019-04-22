# https://github.com/ray-project/ray/blob/master/python/ray/rllib/rollout.py
# copiar o arquivo e registrar o custom env aqui

"""

Example:
    python train_trading_bot.py --algo PPO --symbol ETH
"""


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
from configs.functions import init_data

from trading_gym.trading_env import TradingEnv

# import hypeindx

import ray
from ray.tune import run_experiments, grid_search
from ray.tune.registry import register_env

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='\n')
    parser.add_argument('--symbol', type=str, help='Choose coin to train')
    parser.add_argument('--algo', type=str, help='Choose algorithm to train')
    FLAGS = parser.parse_args()
    keys, symbols = init_data(FLAGS.symbol, 'train')
    # Can also register the env creator function explicitly with:
    register_env("corridor", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "test_{}_{}_{}_{}".format(FLAGS.symbol.upper(),TIME_INTERVAL,FROM_DATE,TO_DATE): {
            "run": FLAGS.algo,
            # "env": TradingEnv,  # or "corridor" if registered above
            "env": "corridor",  # or "corridor" if registered above
            "stop": {
                # "timesteps_total": 1e6,
                "timesteps_total": 1e5,
            },
            "checkpoint_freq": 10,
            "checkpoint_at_end": True,
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