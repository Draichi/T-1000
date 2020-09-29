import ray

import os

import pickle
from utils.data_processing import get_datasets
from ray.tune import grid_search, run
from t_1000.env.trading_env import TradingEnv
from ray.tune.registry import register_env
from ray.rllib.agents.registry import get_agent_class
from t_1000.application.rollout import rollout



env_name = 'YesMan-v1'


def find_results_folder():
    return os.getcwd() + '/results'




def get_instruments_from_checkpoint(checkpoint):
    config = {}
    # Load configuration from file
    config_dir = os.path.dirname(checkpoint)
    config_path = os.path.join(config_dir, "params.pkl")
    if not os.path.exists(config_path):
        config_path = os.path.join(config_dir, "../params.pkl")
    if not os.path.exists(config_path):
        raise ValueError(
            "Could not find params.pkl in either the checkpoint dir or "
            "its parent directory.")
    else:
        with open(config_path, "rb") as f:
            config = pickle.load(f)
    if config['env_config']:
        env_config = config['env_config']
        if env_config['assets']:
            assets = env_config['assets']
        else:
            raise ValueError('assets does not exists in env_config')
        if env_config['currency']:
            currency = env_config['currency']
        else:
            raise ValueError('currency does not exists in env_config')
        if env_config['datapoints']:
            datapoints = env_config['datapoints']
        else:
            raise ValueError('datapoints does not exists in env_config')
        if env_config['granularity']:
            granularity = env_config['granularity']
        else:
            raise ValueError('granularity does not exists in env_config')
    else:
        raise ValueError('env_config does not exists in params.pkl')
    if "num_workers" in config:
        config["num_workers"] = min(2, config["num_workers"])
    return config, assets, currency, datapoints, granularity





class T1000:
    def __init__(self, algo, assets, currency, granularity, datapoints, checkpoint_path, initial_account_balance, exchange_commission, exchange):
        self.algo = algo
        self.assets = assets
        self.currency = currency
        self.granularity = granularity
        self.datapoints = datapoints
        self.df = {}
        self.config_spec = {}
        self.initial_account_balance = initial_account_balance
        self.exchange_commission = exchange_commission
        if checkpoint_path:
            _, self.assets, self.currency, self.datapoints, self.granularity = get_instruments_from_checkpoint(
                checkpoint_path)
        self.check_variables_integrity()
        self.populate_dfs(exchange=exchange)
        self.config_spec_variables = {
            "candlestick_width": {  # constants
                "day": 1,
                "hour": 0.04,
                "minute": 0.0006
            },
            "initial_account_balance": self.initial_account_balance,
            "commission": self.exchange_commission
        }

    def trial_name_string(self, trial):
        return '{}_{}_{}_{}'.format('-'.join(self.assets), self.currency, self.granularity, self.datapoints)

    def check_variables_integrity(self):
        if type(self.assets) != list or len(self.assets) == 0:
            raise ValueError("Incorrect 'assets' value")
        if type(self.currency) != str:
            raise ValueError("Incorrect 'currency' value")
        if type(self.granularity) != str:
            raise ValueError("Incorrect 'granularity' value")
        if type(self.datapoints) != int or 1 > self.datapoints > 2000:
            raise ValueError("Incorrect 'datapoints' value")

    def populate_dfs(self, exchange):
        for asset in self.assets:
            self.df[asset] = {}
            self.df[asset]['train'], self.df[asset]['rollout'] = get_datasets(asset=asset,
                                                                              currency=self.currency,
                                                                              granularity=self.granularity,
                                                                              datapoints=self.datapoints,
                                                                              exchange=exchange)

    def generate_config_spec(self, lr_schedule, df_type):
        self.config_spec = {
            "lr_schedule": grid_search(lr_schedule),
            "env": env_name,
            "num_workers": 3,  # parallelism
            'observation_filter': 'MeanStdFilter',
            'vf_share_layers': True,
            "env_config": {
                'assets': self.assets,
                'currency': self.currency,
                'granularity': self.granularity,
                'datapoints': self.datapoints,
                'df_complete': {},
                'df_features': {},
                'variables': self.config_spec_variables
            },
        }
        self.add_dfs_to_config_spec(df_type=df_type)

    def add_dfs_to_config_spec(self, df_type):
        for asset in self.assets:
            self.config_spec['env_config']['df_complete'][asset] = self.df[asset][df_type]
            self.config_spec['env_config']['df_features'][asset] = self.df[asset][df_type].loc[:,
                                                                                               self.df[asset][df_type].columns != 'Date']

    def backtest(self, checkpoint_path):
        agent_config, assets, currency, datapoints, granularity = get_instruments_from_checkpoint(
            checkpoint_path)

        config = {
            'assets': assets,
            'currency': currency,
            'granularity': granularity,
            'datapoints': datapoints,
            'df_complete': {},
            'df_features': {},
            'variables': self.config_spec_variables
        }

        for asset in assets:
            config['df_complete'][asset] = self.df[asset]['rollout']
            config['df_features'][asset] = self.df[asset]['rollout'].loc[:,
                                                                         self.df[asset]['rollout'].columns != 'Date']

        register_env(env_name, lambda _: TradingEnv(config))
        ray.init()
        cls = get_agent_class(self.algo)
        agent = cls(env=env_name, config=agent_config)
        agent.restore(checkpoint_path)

        num_steps = int(len(config['df_complete'][assets[0]]))
        no_render = False

        rollout(agent, env_name, num_steps, no_render)

    def train(self, timesteps, checkpoint_freq, lr_schedule):
        register_env(env_name, lambda config: TradingEnv(config))
        ray.init()

        self.generate_config_spec(lr_schedule=lr_schedule, df_type='train')

        run(name="t-1000",
            run_or_experiment=self.algo,
            checkpoint_at_end=True,
            stop={'timesteps_total': timesteps},
            checkpoint_freq=checkpoint_freq,
            config=self.config_spec,
            local_dir=find_results_folder(),
            trial_name_creator=self.trial_name_string)
