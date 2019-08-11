import ray
import collections
import os
import pickle
import pandas as pd
from configs.functions import get_datasets
from ray.tune.registry import register_env
# ! run só para ray 0.7 e nao ta funcionando
# from ray.tune import grid_search, run
from ray.tune import grid_search, run_experiments
from env.YesMan import TradingEnv

from ray.rllib.agents.registry import get_agent_class
from ray.rllib.env import MultiAgentEnv
from ray.rllib.env.base_env import _DUMMY_AGENT_ID
from ray.rllib.evaluation.sample_batch import DEFAULT_POLICY_ID
from ray.tune.util import merge_dicts
from ray.tune.registry import register_env

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
        self.config_spec = {}
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
        self.config_spec = {
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
                'df_complete': {},
                'df_features': {}
            },
        }
        self.add_dfs_to_config_spec(df_type='train')

    def add_dfs_to_config_spec(self, df_type):
        for asset in self.assets:
            self.config_spec['env_config']['df_complete'][asset] = self.df[asset][df_type]
            self.config_spec['env_config']['df_features'][asset] = self.df[asset][df_type].loc[:,
                                                                                               self.df[asset][df_type].columns != 'Date']

    def train(self, algo='PPO', timesteps=3e10, checkpoint_freq=100, lr_schedule=[[[0, 7e-5], [3e10, 7e-6]]]):
        register_env("YesMan-v1", lambda config: TradingEnv(config))
        ray.init()

        self.generate_config_spec(lr_schedule)

        # ! ray==6 functiona o run_experiments mas nao o run que nao functiona com nenhuma versao

        # run(name="experiment_name",
        #     run_or_experiment="PPO",
        #     stop={'timesteps_total': timesteps},
        #     checkpoint_freq=100,
        #     config=self.config_spec)
        experiment_name = 'agora_vai'
        config_spec = {
            experiment_name: {
                "run": "PPO",
                "env": "YesMan-v1",
                "stop": {
                    "timesteps_total": 1e6,  # 1e6 = 1M
                },
                "checkpoint_freq": 10,
                "checkpoint_at_end": True,
                "local_dir": os.getcwd() + '/logs',
                "config": {
                    "lr_schedule": grid_search(lr_schedule),
                    'num_workers': 1,  # parallelism
                    'observation_filter': 'MeanStdFilter',
                    'vf_share_layers': True,  # testing
                    "env_config": {
                        'assets': self.assets,
                        'currency': self.currency,
                        'granularity': self.granularity,
                        'datapoints': self.datapoints,
                        'df_complete': {},
                        'df_features': {}
                    },
                }
            }
        }

        for asset in self.assets:
            config_spec[experiment_name]['config']['env_config']['df_complete'][asset] = self.df[asset]['train']
            config_spec[experiment_name]['config']['env_config']['df_features'][asset] = self.df[asset]['train'].loc[:,
                                                                                                           self.df[asset]['train'].columns != 'Date']
        run_experiments(experiments=config_spec)

    def run(self, args, num_steps):
        config = {}
        # Load configuration from file
        config_dir = os.path.dirname(args['checkpoint'])
        config_path = os.path.join(config_dir, "params.pkl")
        if not os.path.exists(config_path):
            config_path = os.path.join(config_dir, "../params.pkl")
        # if not os.path.exists(config_path):
        #     if not args['config']:
        #         raise ValueError(
        #             "Could not find params.pkl in either the checkpoint dir or "
        #             "its parent directory.")
        else:
            with open(config_path, "rb") as f:
                config = pickle.load(f)
        if "num_workers" in config:
            config["num_workers"] = min(2, config["num_workers"])
        config = merge_dicts(config, args['config'])
        if not args['env']:
            # if not config.get("env"):
            #     parser.error("the following arguments are required: --env")
            args.env = config.get("env")

        ray.init()

        cls = get_agent_class(args['run'])
        agent = cls(env=args['env'], config=config)
        print(args['checkpoint'])
        agent.restore(args['checkpoint'])
        num_steps = int(len(num_steps))
        self.rollout(agent, args['env'], num_steps)

    def default_policy_agent_mapping(self):
        return DEFAULT_POLICY_ID

    def rollout(self, agent, env_name, num_steps, out=None, no_render=True):
        policy_agent_mapping = self.default_policy_agent_mapping()

        if hasattr(agent, "local_evaluator"):
            env = agent.local_evaluator.env
            multiagent = isinstance(env, MultiAgentEnv)
            if agent.local_evaluator.multiagent:
                policy_agent_mapping = agent.config["multiagent"][
                    "policy_mapping_fn"]

            policy_map = agent.local_evaluator.policy_map
            state_init = {p: m.get_initial_state()
                          for p, m in policy_map.items()}
            use_lstm = {p: len(s) > 0 for p, s in state_init.items()}
            action_init = {
                p: m.action_space.sample()
                for p, m in policy_map.items()
            }
        else:
            env = gym.make(env_name)
            multiagent = False
            use_lstm = {DEFAULT_POLICY_ID: False}

        if out is not None:
            rollouts = []
        steps = 0
        while steps < (num_steps or steps + 1):
            mapping_cache = {}  # in case policy_agent_mapping is stochastic
            if out is not None:
                rollout = []
            obs = env.reset()
            agent_states = DefaultMapping(
                lambda agent_id: state_init[mapping_cache[agent_id]])
            prev_actions = DefaultMapping(
                lambda agent_id: action_init[mapping_cache[agent_id]])
            prev_rewards = collections.defaultdict(lambda: 0.)
            done = False
            reward_total = 0.0
            while not done and steps < (num_steps or steps + 1):
                multi_obs = obs if multiagent else {_DUMMY_AGENT_ID: obs}
                action_dict = {}
                for agent_id, a_obs in multi_obs.items():
                    if a_obs is not None:
                        policy_id = mapping_cache.setdefault(
                            agent_id, policy_agent_mapping(agent_id))
                        p_use_lstm = use_lstm[policy_id]
                        if p_use_lstm:
                            a_action, p_state, _ = agent.compute_action(
                                a_obs,
                                state=agent_states[agent_id],
                                prev_action=prev_actions[agent_id],
                                prev_reward=prev_rewards[agent_id],
                                policy_id=policy_id)
                            agent_states[agent_id] = p_state
                        else:
                            a_action = agent.compute_action(
                                a_obs,
                                prev_action=prev_actions[agent_id],
                                prev_reward=prev_rewards[agent_id],
                                policy_id=policy_id)
                        action_dict[agent_id] = a_action
                        prev_actions[agent_id] = a_action
                action = action_dict

                action = action if multiagent else action[_DUMMY_AGENT_ID]
                next_obs, reward, done, _ = env.step(action)
                if multiagent:
                    for agent_id, r in reward.items():
                        prev_rewards[agent_id] = r
                else:
                    prev_rewards[_DUMMY_AGENT_ID] = reward

                if multiagent:
                    done = done["__all__"]
                    reward_total += sum(reward.values())
                else:
                    reward_total += reward
                if not no_render:
                    env.render()
                if out is not None:
                    rollout.append([obs, action, next_obs, reward, done])
                steps += 1
                obs = next_obs
            if out is not None:
                rollouts.append(rollout)
            print("Episode reward", reward_total)

        if out is not None:
            pickle.dump(rollouts, open(out, "wb"))

    def backtest(self, checkpoint_file):
        config = {
            'assets': self.assets,
            'currency': self.currency,
            'granularity': self.granularity,
            'datapoints': self.datapoints,
            'df_complete': {},
            'df_features': {},
            # "df1": df1,
            # "df2": df2,
            # "df3": df3,
            # 's1': SYMBOL_1,
            # 's2': SYMBOL_2,
            # 's3': SYMBOL_3,
            # 'trade_instrument': TRADE_INTRUMENT,
            # "render_title": 'Back testing',
            # "histo": HISTO
        }
        for asset in self.assets:
            config['df_complete'][asset] = self.df[asset]['rollout']
            config['df_features'][asset] = self.df[asset]['rollout'].loc[:,
                                                                         self.df[asset]['rollout'].columns != 'Date']
        # ! error here
        # !   File "/home/lucas/Documents/cryptocurrency_prediction/env/YesMan.py", line 63, in __init__
            # ! first_df_columns = self.df_features[self.assets_list[0]].columns
            # ! KeyError: 'OMG'
        register_env("TradingEnv-v0", lambda _: TradingEnv(config))
        args = {
            'env': 'TradingEnv-v0',
            'run': 'PPO',
            'checkpoint': checkpoint_file,
            'config': {}
        }
        self.run(args, self.df[self.assets[0]]['rollout'])

class DefaultMapping(collections.defaultdict):
    """default_factory now takes as an argument the missing key."""

    def __missing__(self, key):
        self[key] = value = self.default_factory(key)
        return value