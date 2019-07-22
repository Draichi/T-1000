import ray
from configs.functions import get_datasets
from ray.tune.registry import register_env
from ray.tune import grid_search, run
from env.YesMan import TradingEnv

# ! ray 0.7.2 => user o run() e nao mais o run_experiments() https://ray.readthedocs.io/en/latest/tune-package-ref.html


# ? ja mandar as dfs separadas por asset para o GymEnv

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
            self.df[asset] = {}
            self.df[asset]['train'], self.df[asset]['rollout'] = get_datasets(asset=asset,
                                                                              currency=self.currency,
                                                                              granularity=self.granularity,
                                                                              datapoints=self.datapoints)

    def generate_config_spec(self, lr_schedule):
        config_spec = {
            "lr_schedule": grid_search(lr_schedule),
            "env": "YesMan-v1",
            "num_workers": 3,  # parallelism
            'observation_filter': 'MeanStdFilter',
            'vf_share_layers': True,
            "env_config": {
                'assets': self.assets,
                'currency': self.currency,
                'granularity': self.granularity,
                'datapoints': self.datapoints,
                # 'df': self.df
            },
        }
        for asset in self.assets:
            config_spec['env_config'][asset] = self.df[asset]

        return config_spec

    def train(self, algo='PPO', timesteps=3e10, checkpoint_freq=100, lr_schedule=[[[0, 7e-5], [3e10, 7e-6]]]):
        register_env("YesMan-v1", lambda config: TradingEnv(config))
        ray.init()

        config_spec = self.generate_config_spec(lr_schedule)

        print(config_spec)
        quit()
        run(name="experiment_name",
            run_or_experiment="PPO",
            stop={'timesteps_total': timesteps},
            checkpoint_freq=100,
            config=config_spec)
