import gym

from stable_baselines.common.policies import MlpPolicy
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import PPO2
from configs.functions import get_datasets

from env.MultiModelEnv import TradingEnv

import pandas as pd

df1, _ = get_datasets('BTC', 'USDT', 'hour', 800)
df2, _ = get_datasets('ETH', 'USDT', 'hour', 800)
df3, _ = get_datasets('LTC', 'USDT', 'hour', 800)
config = {
    'df1': df1,
    'df2': df2,
    'df3': df3,
    'render_title': ''
}
# The algorithms require a vectorized environment to run
env = DummyVecEnv([lambda: TradingEnv(config)])

model = PPO2(MlpPolicy, env, verbose=1)
model.learn(total_timesteps=50)

obs = env.reset()
for i in range(len(df1['Date'])):
    action, _states = model.predict(obs)
    obs, rewards, done, info = env.step(action)
    env.render(title="MSFT")