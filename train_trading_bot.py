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
import os
import ray
from gym.spaces import Discrete, Box
from sklearn.preprocessing import normalize
from configs.vars import *
from configs.functions import init_data
from trading_gym.trading_env import SimpleTradingEnv
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
    register_env("TradingEnv-v1", lambda config: SimpleTradingEnv(config))
    ray.init()
    run_experiments({
        "trading_{}BTC".format(FLAGS.symbol): {
            "run": FLAGS.algo,
            # "env": TradingEnv,  # or "corridor" if registered above
            "env": "TradingEnv-v1",  # or "corridor" if registered above
            "stop": {
                "timesteps_total": 1.2e6, #1e6 = 1M
            },
            "checkpoint_freq": 100,
            "checkpoint_at_end": True,
            "config": {
                "lr": grid_search([
                    1e-5,
                    2e-5
                ]),
                "num_workers": 3,  # parallelism
                'observation_filter': 'MeanStdFilter',
                "env_config": {
                    'keys': keys,
                    'symbols': symbols
                },
            }
        }
    })