"""Gym enrivornment to simulate trading operations with multi pairs.

This environment use an array rank 1 with 220 items as it's observations space.

Lucas Draichi
2019
"""

import random
import json
import gym
from gym import spaces
from configs.vars import LOOKBACK_WINDOW_SIZE, INITIAL_ACCOUNT_BALANCE, COMMISSION
import pandas as pd
import numpy as np
from termcolor import colored
import colorama
colorama.init()
from env.MultiModelRenderRank1V2 import StockTradingGraph
# from env.MultiModelRenderRank1 import StockTradingGraph

class TradingEnv(gym.Env):
    """A stock trading environment for OpenAI gym"""
    # metadata = {'render.modes': ['live', 'file', 'none']}
    visualization = None

    def __init__(self, config):
        # print(config)
        self.df1 = config['df1']
        self.df1_features = self.df1.loc[: , self.df1.columns != 'Date']
        self.df2 = config['df2']
        self.df2_features = self.df2.loc[: , self.df2.columns != 'Date']
        self.df3 = config['df3']
        self.df3_features = self.df3.loc[: , self.df3.columns != 'Date']
        self.render_title = config['render_title']
        self.histo = config['histo']
        self.s1, self.s2, self.s3 = config['s1'], config['s2'], config['s3']
        self.trade_instrument = config['trade_instrument']
        self.lookback_window_size = LOOKBACK_WINDOW_SIZE
        self.initial_balance = INITIAL_ACCOUNT_BALANCE
        self.commission = COMMISSION
        self.serial = False
        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([7, 1]), # buy and sell each of these 3 coins and hold position = 7 posible actions
            dtype=np.float16)
        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max,
            high=np.finfo(np.float32).max,
            shape=(len(self.df1_features.columns) * 3 + 13, ), # shape = 3 dfs * len(df) + obs variables
            dtype=np.float16)

    def _next_observation(self):
        frame1 = np.array(self.df1_features.values[self.current_step])
        frame2 = np.array(self.df2_features.values[self.current_step])
        frame3 = np.array(self.df3_features.values[self.current_step])
        # frame = frame1 + frame2 + frame3
        frame = np.concatenate((frame1, frame2, frame3))
        # print('============ \n',len(frame))
        # print(frame)
        obs = np.append(frame, [
            [self.balance],
            [self.shares1_bought],
            [self.shares2_bought],
            [self.shares3_bought],
            [self.shares1_sold],
            [self.shares2_sold],
            [self.shares3_sold],
            [self.shares1_held],
            [self.shares2_held],
            [self.shares3_held],
            [self.cost],
            [self.sales],
            [self.net_worth]
        ])
        # print('============ \n',len(self.df1_features.columns) * 3 + 13)
        # print('\n', len(obs))
        # print(obs)
        # print('==============\n')
        return obs

    def _take_action(self, action):
        current_price1 = random.uniform(
            self.df1_features.loc[self.current_step, "open"], self.df1_features.loc[self.current_step, "close"])
        current_price2 = random.uniform(
            self.df2_features.loc[self.current_step, "open"], self.df2_features.loc[self.current_step, "close"])
        current_price3 = random.uniform(
            self.df3_features.loc[self.current_step, "open"], self.df3_features.loc[self.current_step, "close"])

        action_type = action[0]
        amount = action[1]

        if 0 < amount <= 1 and action_type > 0: # bounds of action_space doesn't seem to work, so this line is necessary to not overflow actions

            self.shares1_bought = 0
            self.shares2_bought = 0
            self.shares3_bought = 0
            self.shares1_sold = 0
            self.shares2_sold = 0
            self.shares3_sold = 0
            self.cost = 0
            self.sales = 0

            # buy shares1
            if action_type < 1 and self.balance >= self.balance * amount * (1 + self.commission): # check if has enough money to trade
                self.shares1_bought = self.balance * amount / current_price1
                self.cost = self.shares1_bought * current_price1 * (1 + self.commission)
                self.shares1_held += self.shares1_bought
                self.balance -= self.cost
            # sell shares1
            elif action_type < 2:
                self.shares1_sold = self.shares1_held * amount
                self.sales = self.shares1_sold * current_price1 * (1 - self.commission)
                self.shares1_held -= self.shares1_sold
                self.balance += self.sales

            # buy shares 2
            elif action_type < 3 and self.balance >= self.balance * amount * (1 + self.commission): # check if has enough money to trade
                self.shares2_bought = self.balance * amount / current_price2
                self.cost = self.shares2_bought * current_price2 * (1 + self.commission)
                self.shares2_held += self.shares2_bought
                self.balance -= self.cost
            # sell shares 2
            elif action_type < 4:
                self.shares2_sold = self.shares2_held * amount
                self.sales = self.shares2_sold * current_price2 * (1 - self.commission)
                self.shares2_held -= self.shares2_sold
                self.balance += self.sales

            # buy shares 3
            elif action_type < 5 and self.balance >= self.balance * amount * (1 + self.commission): # check if has enough money to trade
                self.shares3_bought = self.balance * amount / current_price3
                self.cost = self.shares3_bought * current_price3 * (1 + self.commission)
                self.shares3_held += self.shares3_bought
                self.balance -= self.cost
            # sell shares 3
            elif action_type < 6:
                self.shares3_sold = self.shares3_held * amount
                self.sales = self.shares3_sold * current_price3 * (1 - self.commission)
                self.shares3_held -= self.shares3_sold
                self.balance += self.sales

            if self.shares1_sold > 0 or self.shares1_bought > 0:
                # only print in rollout mode
                # print(colored('{} BTC {} USDT - holding: {} BTC balance {} USDT'.format(self.shares1_bought, self.cost if self.shares1_bought > 0 else self.sales, self.shares1_held, self.balance), 'green' if self.shares1_bought > 0 else 'red'))
                self.trades1.append({'step': self.current_step,
                                    'amount': self.shares1_sold if self.shares1_sold > 0 else self.shares1_bought, 'total': self.sales if self.shares1_sold > 0 else self.cost,
                                    'type': "sell" if self.shares1_sold > 0 else "buy"})
            if self.shares2_sold > 0 or self.shares2_bought > 0:
                # print(colored('{} ETH {} USDT - holding {} ETH balance: {} USDT'.format(self.shares2_bought, self.cost if self.shares2_bought > 0 else self.sales, self.shares2_held, self.balance), 'green' if self.shares2_bought > 0 else 'red'))
                self.trades2.append({'step': self.current_step,
                                    'amount': self.shares2_sold if self.shares2_sold > 0 else self.shares2_bought, 'total': self.sales if self.shares2_sold > 0 else self.cost,
                                    'type': "sell" if self.shares2_sold > 0 else "buy"})
            if self.shares3_sold > 0 or self.shares3_bought > 0:
                # print(colored('{} LTC {} USDT - holding {} LTC balance: {} USDT'.format(self.shares3_bought, self.cost if self.shares3_bought > 0 else self.sales, self.shares3_held, self.balance), 'green' if self.shares3_bought > 0 else 'red'))
                self.trades3.append({'step': self.current_step,
                                    'amount': self.shares3_sold if self.shares3_sold > 0 else self.shares3_bought, 'total': self.sales if self.shares3_sold > 0 else self.cost,
                                    'type': "sell" if self.shares3_sold > 0 else "buy"})

        self.net_worth = self.balance + (self.shares1_held * current_price1) + (self.shares2_held * current_price2) + (self.shares3_held * current_price3)
        self.buy_and_hold = self.initial_bought1 * current_price1 + self.initial_bought2 * current_price2 + self.initial_bought3 * current_price3

    def step(self, action):
        # Execute one time step within the environment
        self._take_action(action)
        self.current_step += 1

        net_worth_and_buyhold_mean = (self.net_worth + self.buy_and_hold) / 2
        reward = (self.net_worth - self.buy_and_hold) / net_worth_and_buyhold_mean
        done = self.net_worth <= 0 or self.balance <= 0 or self.current_step >= len(self.df1_features.loc[:, 'open'].values) -1
        obs = self._next_observation()

        return obs, reward, done, {}

    def reset(self):
        # Reset the state of the environment to an initial state
        self.balance = INITIAL_ACCOUNT_BALANCE
        self.net_worth = INITIAL_ACCOUNT_BALANCE
        self.shares1_held = 0
        self.shares2_held = 0
        self.shares3_held = 0
        self.shares1_bought = 0
        self.shares2_bought = 0
        self.shares3_bought = 0
        self.shares1_sold = 0
        self.shares2_sold = 0
        self.shares3_sold = 0
        self.cost = 0
        self.sales = 0
        self.current_step = 0
        self.first_price1 = self.df1_features["close"][0]
        self.first_price2 = self.df2_features["close"][0]
        self.first_price3 = self.df3_features["close"][0]
        self.initial_bought1 = 1/3 * self.initial_balance / self.first_price1
        self.initial_bought2 = 1/3 * self.initial_balance / self.first_price2
        self.initial_bought3 = 1/3 * self.initial_balance / self.first_price3
        self.trades1 = []
        self.trades2 = []
        self.trades3 = []

        return self._next_observation()

    def _render_to_file(self, filename='render.txt'):
        profit = self.net_worth - INITIAL_ACCOUNT_BALANCE

        file = open(filename, 'a+')

        file.write('Step: {}\n'.format(self.current_step))
        file.write('Balance: {}\n'.format(self.balance))
        file.write('Shares1 held: {}\n'.format(self.shares1_held))
        file.write('Shares2 held: {}\n'.format(self.shares2_held))
        file.write('Shares3 held: {}\n'.format(self.shares3_held))
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
                self.visualization = StockTradingGraph(self.df1,
                                                       self.df2,
                                                       self.df3,
                                                       self.render_title,
                                                       self.histo,
                                                       self.s1,
                                                       self.s2,
                                                       self.s3,
                                                       self.trade_instrument)

            # if self.current_step > LOOKBACK_WINDOW_SIZE:
            self.visualization.render(self.current_step,
                                      self.net_worth,
                                      self.buy_and_hold,
                                      self.trades1,
                                      self.trades2,
                                      self.trades3,
                                      self.shares1_held,
                                      self.shares2_held,
                                      self.shares3_held,
                                      self.balance,
                                      window_size=LOOKBACK_WINDOW_SIZE)

    def close(self):
        if self.visualization != None:
            self.visualization.close()
            self.visualization = None
