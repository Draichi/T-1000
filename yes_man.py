from configs.functions import get_datasets
from ray.tune.registry import register_env, grid_search
from env.YesMan import TradingEnv


class Trade:
    """Fertile environment to trade cryptos via algorithm"""

    def __init__(self, assets=['BTC', 'LTC', 'ETH'], currency='USDT', granularity='day', datapoints=600):

        self.assets = assets
        self.currency = currency
        self.granularity = granularity
        self.datapoints = datapoints
        self.df = {}
        self.check_variables_integrity()
        self.populate_dfs()

    def check_variables_integrity(self):
        if type(self.assets) != list or len(self.assets) == 0:
            raise ValueError("Incorrect 'assets' value")
        if type(self.currency) != str:
            raise ValueError("Incorrect 'currency' value")
        if type(self.granularity) != str:
            raise ValueError("Incorrect 'granularity' value")
        if type(self.datapoints) != int or 1 > self.datapoints > 2000:
            raise ValueError("Incorrect 'datapoints' value")

    def populate_dfs(self):
        for asset in self.assets:
            df_train = asset + '_train'
            df_rollout = asset + '_rollout'
            self.df[df_train], self.df[df_rollout] = get_datasets(asset=asset,
                                                                  currency=self.currency,
                                                                  granularity=self.granularity,
                                                                  datapoints=self.datapoints)

    def train(self, algo='PPO', timesteps=3e10, checkpoint_freq=100, lr_schedule=[[[0, 7e-5], [3e10, 7e-6]]]):

        register_env("YesMan-v1", lambda config: TradingEnv(config))
        experiment_spec = {
            "": {
                "run": "PPO",
                "env": "MultiTradingEnv-v1",
                "stop": {
                    "timesteps_total": TIMESTEPS_TOTAL,  # 1e6 = 1M
                },
                "checkpoint_freq": CHECKPOINT_FREQUENCY,
                "checkpoint_at_end": True,
                # you can comment this line and your chapoints will be saved in ~/ray_results/
                "local_dir": '/home/lucas/Documents/cryptocurrency_prediction/tensorboard',
                # "restore": RESTORE_PATH,
                "config": {
                    "lr_schedule": grid_search(LEARNING_RATE_SCHEDULE),
                    "num_workers": 3,  # parallelism
                    'observation_filter': 'MeanStdFilter',
                    'vf_share_layers': True,  # testing
                    "env_config": {
                        'df': self.df,
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
        # run_experiments(experiments=experiment_spec)
        run_experiments(name="experiment_name",
                        run="PPO",
                        env="YesMan-v1",
                        stop={'timesteps_total': timesteps},
                        checkpoint_freq=100,
                        config={
                            "lr_schedule": grid_search(LEARNING_RATE_SCHEDULE),
                            "num_workers": 3,  # parallelism
                            'observation_filter': 'MeanStdFilter',
                            'vf_share_layers': True,  # testing
                            "env_config": {
                                'assets': self.assets,
                                'currency': self.currency,
                                'granularity': self.granularity,
                                'datapoints': self.datapoints
                            },
                        })
