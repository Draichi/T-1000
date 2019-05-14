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
from env.TradingEnvV1 import TradingEnv
from ray.tune import run_experiments, grid_search
from ray.tune.registry import register_env

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='\n train a reinforcement learning agent')
    parser.add_argument('--pair', type=str, required=True, help='The pair to be traded e.g.: ETH/BTC')
    parser.add_argument('--histo', type=str, required=True, help='Daily or hourly data')
    parser.add_argument('--limit', type=int, required=True, help='How many data points')
    parser.add_argument('--algo', type=str, required=True, help='Choose algorithm to train')
    args = parser.parse_args()
    from_symbol, to_symbol = args.pair.split('/')
    df, _ = get_datasets(from_symbol, to_symbol, args.histo, args.limit)
    register_env("TradingEnv-v0", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "{}_{}_{}_{}".format(from_symbol + to_symbol, args.limit, args.histo, date.today()): {
            "run": args.algo,
            "env": "TradingEnv-v0",
            "stop": {
                "timesteps_total": 3e4, #1e6 = 1M
            },
            "checkpoint_freq": 100,
            "checkpoint_at_end": True,
            "config": {
                "lr": grid_search([
                    1e-4
                    # 1e-6
                ]),
                "num_workers": 3,  # parallelism
                'observation_filter': 'MeanStdFilter',
                # "vf_clip_param": 10000000.0,
                "env_config": {
                    'df': df,
                    'render_title': ''
                },
            }
        }
    })