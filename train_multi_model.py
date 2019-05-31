"""Script to train an agent to operate into the market and trade between 3 diffrent pairs.

Update the variables at configs/vars.py.

Example:
    python train_multi_model.py

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
from env.MultiModelEnvRank1 import TradingEnv

# https://github.com/ray-project/ray/blob/master/python/ray/rllib/train.py

if __name__ == "__main__":
    df1, _ = get_datasets(SYMBOL_1, TRADE_INTRUMENT, HISTO, LIMIT)
    df2, _ = get_datasets(SYMBOL_2, TRADE_INTRUMENT, HISTO, LIMIT)
    df3, _ = get_datasets(SYMBOL_3, TRADE_INTRUMENT, HISTO, LIMIT)
    register_env("MultiTradingEnv-v1", lambda config: TradingEnv(config))
    experiment_spec = {
        "{}-{}-{}-{}_{}_{}_{}".format(SYMBOL_1, SYMBOL_2, SYMBOL_3, TRADE_INTRUMENT, HISTO, LIMIT, date.today()): {
            "run": "PPO",
            "env": "MultiTradingEnv-v1",
            "stop": {
                "timesteps_total": TIMESTEPS_TOTAL, #1e6 = 1M
            },
            "checkpoint_freq": CHECKPOINT_FREQUENCY,
            "checkpoint_at_end": True,
            "local_dir": '/home/lucas/Documents/cryptocurrency_prediction/tensorboard',
            "restore": RESTORE_PATH,
            "config": {
                "lr_schedule": grid_search(LEARNING_RATE_SCHEDULE),
                "num_workers": 3, # parallelism
                'observation_filter': 'MeanStdFilter',
                'vf_share_layers': True, # testing
                "env_config": {
                    'df1': df1,
                    'df2': df2,
                    'df3': df3,
                    's1': SYMBOL_1,
                    's2': SYMBOL_2,
                    's3': SYMBOL_3,
                    'trade_instrument': TRADE_INSTRUMENT,
                    'render_title': '',
                    'histo': HISTO
                },
            }
        }
    }
    ray.init()
    run_experiments(experiments=experiment_spec)