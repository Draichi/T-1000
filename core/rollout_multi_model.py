"""Script to evaluate previourly trained agents

Example:
    python rollout_multi_model.py ./tensorboard/LTC-ETH-OMG-USDT_minute_1500_2019-05-31/PPO_MultiTradingEnv-v1_0_lr_schedule=1100000_7e-05_3500000_7e-06_2019-05-31_09-45-52_jyp06hp/checkpoint_875/checkpoint-875 \
        --run PPO \
        --env TradingEnv-v0

Lucas Draichi 2019
"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import collections
import json
import os
import pickle
import gym
import ray
from configs.functions import get_datasets
from configs.vars import *
from ray.rllib.agents.registry import get_agent_class
from ray.rllib.env import MultiAgentEnv
from ray.rllib.env.base_env import _DUMMY_AGENT_ID
from ray.rllib.evaluation.sample_batch import DEFAULT_POLICY_ID
from ray.tune.util import merge_dicts
from ray.tune.registry import register_env
from env.MultiModelEnvRank1 import TradingEnv

EXAMPLE_USAGE = """
    rollout_multi_model.py /tmp/ray/checkpoint_dir/checkpoint-0 --run PPO
    --env TradingEnv-v0
"""

def create_parser(parser_creator=None):
    parser_creator = parser_creator or argparse.ArgumentParser
    parser = parser_creator(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Roll out a reinforcement learning agent "
        "given a checkpoint.",
        epilog=EXAMPLE_USAGE)

    parser.add_argument(
        "checkpoint", type=str, help="Checkpoint from which to roll out.")
    required_named = parser.add_argument_group("required named arguments")
    required_named.add_argument(
        "--run",
        type=str,
        required=True,
        help="The algorithm or model to train. This may refer to the name "
        "of a built-on algorithm (e.g. RLLib's DQN or PPO), or a "
        "user-defined trainable function or class registered in the "
        "tune registry.")
    required_named.add_argument(
        "--env", type=str, required=True, help="The gym environment to use.")
    parser.add_argument(
        "--no-render",
        default=False,
        action="store_const",
        const=True,
        help="Surpress rendering of the environment.")
    # parser.add_argument(
    #     "--steps", default=10000, help="Number of steps to roll out.")
    parser.add_argument("--out", default=None, help="Output filename.")
    parser.add_argument(
        "--config",
        default="{}",
        type=json.loads,
        help="Algorithm-specific configuration (e.g. env, hyperparams). "
        "Surpresses loading of configuration from checkpoint.")
    return parser


def run(args, parser, num_steps):
    config = {}
    # Load configuration from file
    config_dir = os.path.dirname(args.checkpoint)
    config_path = os.path.join(config_dir, "params.pkl")
    if not os.path.exists(config_path):
        config_path = os.path.join(config_dir, "../params.pkl")
    if not os.path.exists(config_path):
        if not args.config:
            raise ValueError(
                "Could not find params.pkl in either the checkpoint dir or "
                "its parent directory.")
    else:
        with open(config_path, "rb") as f:
            config = pickle.load(f)
    if "num_workers" in config:
        config["num_workers"] = min(2, config["num_workers"])
    config = merge_dicts(config, args.config)
    if not args.env:
        if not config.get("env"):
            parser.error("the following arguments are required: --env")
        args.env = config.get("env")

    ray.init()

    cls = get_agent_class(args.run)
    agent = cls(env=args.env, config=config)
    agent.restore(args.checkpoint)
    num_steps = int(len(num_steps))
    rollout(agent, args.env, num_steps, args.out, args.no_render)


class DefaultMapping(collections.defaultdict):
    """default_factory now takes as an argument the missing key."""

    def __missing__(self, key):
        self[key] = value = self.default_factory(key)
        return value


def default_policy_agent_mapping(unused_agent_id):
    return DEFAULT_POLICY_ID


def rollout(agent, env_name, num_steps, out=None, no_render=True):
    policy_agent_mapping = default_policy_agent_mapping

    if hasattr(agent, "local_evaluator"):
        env = agent.local_evaluator.env
        multiagent = isinstance(env, MultiAgentEnv)
        if agent.local_evaluator.multiagent:
            policy_agent_mapping = agent.config["multiagent"][
                "policy_mapping_fn"]

        policy_map = agent.local_evaluator.policy_map
        state_init = {p: m.get_initial_state() for p, m in policy_map.items()}
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


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    _ ,df1 = get_datasets(SYMBOL_1, TRADE_INTRUMENT, HISTO, LIMIT)
    _ ,df2 = get_datasets(SYMBOL_2, TRADE_INTRUMENT, HISTO, LIMIT)
    _ ,df3 = get_datasets(SYMBOL_3, TRADE_INTRUMENT, HISTO, LIMIT)
    config = {
        "df1": df1,
        "df2": df2,
        "df3": df3,
        's1': SYMBOL_1,
        's2': SYMBOL_2,
        's3': SYMBOL_3,
        'trade_instrument': TRADE_INTRUMENT,
        "render_title": 'Back testing',
        "histo": HISTO
    }
    register_env("TradingEnv-v0", lambda _: TradingEnv(config))
    run(args, parser, df1)