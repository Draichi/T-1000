import random
import json
import gym
from gym import spaces
from configs.vars import LOOKBACK_WINDOW_SIZE, INITIAL_ACCOUNT_BALANCE, COMMISSION
import pandas as pd
import numpy as np
from env.TradingRenderV1 import StockTradingGraph

class TradingEnv(gym.Env):
    """A stock trading environment for OpenAI gym"""
    # metadata = {'render.modes': ['live', 'file', 'none']}

    def __init__(self, config):
        self.df = config['df']
        self.df_features = self.df.loc[: , self.df.columns != 'Date']
        self.render_title = config['render_title']
        self.lookback_window_size = LOOKBACK_WINDOW_SIZE
        self.initial_balance = INITIAL_ACCOUNT_BALANCE
        self.commission = COMMISSION
        self.serial = False
        self.visualization = None
        self.total_steps = len(self.df_features.loc[:, 'open'].values) -1
        self.action_space = spaces.Box(
            low=np.array([0, 0]), high=np.array([3, 1]), dtype=np.float16)
        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max, shape=(len(self.df_features.columns) + 7, ), dtype=np.float16) # shape = len(df) + obs variables

    def _next_observation(self):
        frame = np.array(self.df_features.values[self.current_step])

        obs = np.append(frame, [
            [self.balance],
            [self.btc_bought],
            [self.btc_sold],
            [self.cost],
            [self.sales],
            [self.net_worth],
            [self.shares_held]
        ])

        return obs

    def _take_action(self, action):
        current_price = random.uniform(self.df_features.loc[self.current_step, "open"],
                                       self.df_features.loc[self.current_step, "close"])

        action_type = action[0]
        amount = action[1]

        if 0 < amount <= 1 and action_type > 0: # bounds of action_space doesn't seem to work, so this line is necessary to not overflow actions

            self.btc_bought = 0
            self.btc_sold = 0
            self.cost = 0
            self.sales = 0

            if action_type < 1 and self.balance >= self.balance * amount * (1 + self.commission): # check if has enough money to trade

                self.btc_bought = self.balance * amount / current_price
                self.cost = self.btc_bought * current_price * (1 + self.commission)
                self.shares_held += self.btc_bought
                self.balance -= self.cost

            elif action_type < 2:

                self.btc_sold = self.shares_held * amount
                self.sales = self.btc_sold * current_price * (1 - self.commission)
                self.shares_held -= self.btc_sold
                self.balance += self.sales

            if self.btc_sold > 0 or self.btc_bought > 0:
                self.trades.append({'step': self.current_step,
                                    'amount': self.btc_sold if self.btc_sold > 0 else self.btc_bought, 'total': self.sales if self.btc_sold > 0 else self.cost,
                                    'type': "sell" if self.btc_sold > 0 else "buy"})

        self.net_worth = self.balance + self.shares_held * current_price
        self.buy_and_hold = self.initial_bought * current_price

    def _reward(self):
        net_worth_and_buyhold_mean = (self.net_worth + self.buy_and_hold) / 2
        reward = (self.net_worth - self.buy_and_hold) / net_worth_and_buyhold_mean
        return reward

    def step(self, action):
        # Execute one time step within the environment
        self._take_action(action)
        self.current_step += 1

        reward = self._reward()
        done = self.net_worth <= 0 or self.balance <= 0 or self.current_step >= self.total_steps
        obs = self._next_observation()

        return obs, reward, done, {}

    def reset(self):
        # Reset the state of the environment to an initial state
        self.balance = INITIAL_ACCOUNT_BALANCE
        self.net_worth = INITIAL_ACCOUNT_BALANCE
        self.shares_held = 0
        self.btc_bought = 0
        self.btc_sold = 0
        self.cost = 0
        self.sales = 0
        self.current_step = 0
        self.first_price = self.df_features["close"][0]
        self.initial_bought = self.initial_balance / self.first_price
        self.trades = []

        return self._next_observation()

    def _render_to_file(self, filename='render.txt'):
        profit = self.net_worth - INITIAL_ACCOUNT_BALANCE

        file = open(filename, 'a+')

        file.write('Step: {}\n'.format(self.current_step))
        file.write('Balance: {}\n'.format(self.balance))
        file.write('Shares held: {}\n'.format(self.shares_held))
        file.write('Avg cost for held shares: {}\n'.format(self.cost))
        file.write('Net worth: {}\n'.format(self.net_worth))
        file.write('Buy and hold strategy: {}\n'.format(self.buy_and_hold))
        file.write('Profit: {}\n\n'.format(profit))

        file.close()

    def render(self, mode='live', **kwargs):
        # Render the environment to the screen
        if mode == 'file':
            self._render_to_file(kwargs.get('filename', 'render.txt'))

        elif mode == 'live':
            if self.visualization == None:
                self.visualization = StockTradingGraph(self.df, self.render_title)

            # if self.current_step > LOOKBACK_WINDOW_SIZE:
            self.visualization.render(
            self.current_step, self.net_worth, self.buy_and_hold, self.trades, self.shares_held, self.balance, window_size=LOOKBACK_WINDOW_SIZE)

    def close(self):
        if self.visualization != None:
            self.visualization.close()
            self.visualization = None
