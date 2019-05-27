"""Script to train an agent to operate into the market according to the pair

Example:
    python train.py \
        --algo PPO \
        --pair XRP/USDT \
        --histo hour \
        --limit 180

Lucas Draichi 2019
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import pandas as pd
import gym
import os
import ray
from datetime import date
from gym.spaces import Discrete, Box
from configs.functions import get_datasets
from ray.tune import run_experiments, grid_search
from ray.tune.registry import register_env

# choose the multi model env
# from env.MultiModelEnv import TradingEnv
from env.MultiModelEnvRank1 import TradingEnv
s1, s2, s3 = 'BTC', 'ETH', 'LTC'
trade_instrument = 'USDT'

if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser(description='\n train a reinforcement learning agent')
    # parser.add_argument('--pair', type=str, required=True, help='The pair to be traded e.g.: ETH/BTC')
    # parser.add_argument('--histo', type=str, required=True, help='Daily or hourly data')
    # parser.add_argument('--limit', type=int, required=True, help='How many data points')
    # parser.add_argument('--algo', type=str, required=True, help='Choose algorithm to train')
    # args = parser.parse_args()
    # from_symbol, to_symbol = args.pair.split('/')
    df1, _ = get_datasets(s1, trade_instrument, 'hour', 800)
    df2, _ = get_datasets(s2, trade_instrument, 'hour', 800)
    df3, _ = get_datasets(s3, trade_instrument, 'hour', 800)
    register_env("MultiTradingEnv-v0", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "MultimodelRank1": {
            "run": "PPO",
            "env": "MultiTradingEnv-v0",
            "stop": {
                "timesteps_total": 2e6, #1e6 = 1M
            },
            "checkpoint_freq": 50,
            "checkpoint_at_end": True,
            # "conv_filters": [3, 76],
            "config": {
                "lr": grid_search([
                    5e-5,
                    # 5.5e-5,
                    # 4.5e-5,
                    # 4e-5,
                    # 5e-4,
                    # 9e-5
                ]),
                "num_workers": 3,  # parallelism
                'observation_filter': 'MeanStdFilter',
                # "model": {
                #     "dim": 4,
                #     "conv_filters": [[1, [1, 1], 1]],
                #     "use_lstm": True
                # },
                'vf_share_layers': True, # testing
                "env_config": {
                    'df1': df1,
                    'df2': df2,
                    'df3': df3,
                    's1': s1,
                    's2': s2,
                    's3': s3,
                    'trade_instrument': trade_instrument,
                    'render_title': ''
                },
            }
        }
    })