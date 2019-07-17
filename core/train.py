"""Script to train an agent to operate into the market according to the pair

Example:
    python train.py \
        --algo PPO \
        --pair XRP/USDT \

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
from configs.vars import *
from env.TradingEnvV1 import TradingEnv
from ray.tune import run_experiments, grid_search
from ray.tune.registry import register_env

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='\n train a reinforcement learning agent')
    parser.add_argument('--pair', type=str, required=True, help='The pair to be traded e.g.: ETH/BTC')
    parser.add_argument('--algo', type=str, required=True, help='Choose algorithm to train')
    args = parser.parse_args()
    from_symbol, to_symbol = args.pair.split('/')
    df, _ = get_datasets(from_symbol, to_symbol, HISTO, LIMIT)
    register_env("TradingEnv-v0", lambda config: TradingEnv(config))
    ray.init()
    run_experiments({
        "{}_{}_{}_{}".format(from_symbol + to_symbol, LIMIT, HISTO, date.today()): {
            "run": args.algo,
            "env": "TradingEnv-v0",
            "stop": {
                "timesteps_total": TIMESTEPS_TOTAL,
            },
            "checkpoint_freq": CHECKPOINT_FREQUENCY,
            "checkpoint_at_end": True,
            "config": {
                "lr_schedule": grid_search(LEARNING_RATE_SCHEDULE),
                "num_workers": 3,  # parallelism
                'observation_filter': 'MeanStdFilter',
                'vf_share_layers': True, # testing
                # "vf_clip_param": 10000000.0,
                "env_config": {
                    'df': df,
                    'render_title': ''
                },
            }
        }
    })