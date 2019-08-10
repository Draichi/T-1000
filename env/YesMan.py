"""Gym enrivornment to simulate trading operations with multi pairs.

This environment use an array rank 1 with 220 items as it's observations space.

Lucas Draichi
2019
"""

from env.YesManRender import StockTradingGraph
import random
import json
import gym
from gym import spaces
from configs.vars import LOOKBACK_WINDOW_SIZE, INITIAL_ACCOUNT_BALANCE, COMMISSION
import pandas as pd
import numpy as np
from termcolor import colored
import colorama
from configs.functions import get_datasets

colorama.init()
# from env.MultiModelRenderRank1 import StockTradingGraph


class TradingEnv(gym.Env):
    """A stock trading environment for OpenAI gym"""
    # metadata = {'render.modes': ['live', 'file', 'none']}
    visualization = None

    def __init__(self, config):
        self.assets = config['assets'],
        self.assets_list = self.assets[0]
        self.currency = config['currency'],
        self.granularity = config['granularity'],
        self.datapoints = config['datapoints']
        self.df_complete = config['df_complete']
        self.df_features = config['df_features']
        self.shares_held = {}
        self.shares_bought = {}
        self.shares_sold = {}
        self.first_prices = {}
        self.initial_bought = {}
        self.trades = {}
        self.current_price = {}

        # ! colocar apenas data relevante aqui

        # self.render_title = config['render_title']
        # self.lookback_window_size = LOOKBACK_WINDOW_SIZE
        self.initial_balance = INITIAL_ACCOUNT_BALANCE
        self.commission = COMMISSION
        # self.serial = False

        # action space = buy and sell for each asset, pĺus hold position
        action_space = 1 + len(self.assets_list) * 2

        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([action_space, 1]),
            dtype=np.float16)

        # first_asset_of_list = self.assets[0][0]
        first_df_columns = self.df_features[self.assets_list[0]].columns
        # obs space = (number of columns * number of assets) + 4 (balance, cost, sales, net_worth) + (number of assets * 3 (shares bought, shares sold, shares held))
        observation_space = (len(first_df_columns) *
                             len(self.assets_list)) + 4 + (len(self.assets_list) * 3)

        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max,
            high=np.finfo(np.float32).max,
            shape=(observation_space, ),
            dtype=np.float16)

    def reset(self):
        # Reset the state of the environment to an initial state
        self._reset_balance()
        self.current_step = 0
        self._get_first_prices()
        self._compute_initial_bought()
        self._reset_trades()

        return self._next_observation()

    def step(self, action):
        # Execute one time step within the environment
        self._take_action(action)
        self.current_step += 1

        net_worth_and_buyhold_mean = (self.net_worth + self.buy_and_hold) / 2
        reward = (self.net_worth - self.buy_and_hold) / \
            net_worth_and_buyhold_mean
        done = self.net_worth <= 0 or self.balance <= 0 or self.current_step >= len(
            self.df_features[self.assets_list[0]].loc[:, 'open'].values) - 1
        obs = self._next_observation()

        return obs, reward, done, {}

    def _reset_trades(self):
        for asset in self.assets_list:
            self.trades[asset] = []

    def _compute_initial_bought(self):
        """spread the initial account balance through all assets"""
        for asset in self.assets_list:
            self.initial_bought[asset] = 1/len(self.assets_list) * \
                self.initial_balance / self.first_prices[asset]

    def _get_first_prices(self):
        for asset in self.assets_list:
            self.first_prices[asset] = self.df_features[asset]['close'][0]

    def _reset_shares_bought_n_sold(self):
        for asset in self.assets_list:
            self.shares_bought[asset] = 0.0
            self.shares_sold[asset] = 0.0

    def _reset_cost_n_sales(self):
        self.cost = 0
        self.sales = 0

    def _reset_balance(self):
        self._reset_cost_n_sales()
        self.balance = INITIAL_ACCOUNT_BALANCE
        self.net_worth = INITIAL_ACCOUNT_BALANCE
        for asset in self.assets_list:
            self.shares_held[asset] = 0.0
            self.shares_bought[asset] = 0.0
            self.shares_sold[asset] = 0.0

    def _next_observation(self):
        shares_bought = np.array([self.shares_bought[asset]
                                  for asset in self.assets_list])
        shares_sold = np.array([self.shares_sold[asset]
                                for asset in self.assets_list])
        shares_held = np.array([self.shares_held[asset]
                                for asset in self.assets_list])

        current_row_of_all_dfs = np.concatenate([np.array(
            self.df_features[asset].values[self.current_step]) for asset in self.assets_list])

        observation_without_shares = np.append(current_row_of_all_dfs, [
            self.balance,
            self.cost,
            self.sales,
            self.net_worth
        ])
        observation = np.append(observation_without_shares, [
                                shares_bought, shares_held, shares_sold])
        return observation

    def _compute_current_price(self):
        for asset in self.assets_list:
            self.current_price[asset] = random.uniform(self.df_features[asset].loc[self.current_step, 'open'],
                                                       self.df_features[asset].loc[self.current_step, 'close'])

    def _buy(self, asset, amount):
        self.shares_bought[asset] = self.balance * \
            amount / self.current_price[asset]
        self.cost = self.shares_bought[asset] * \
            self.current_price[asset] * (1 + self.commission)
        self.shares_held[asset] += self.shares_bought[asset]
        self.balance -= self.cost
        return True

    def _sell(self, asset, amount):
        self.shares_sold[asset] = self.shares_held[asset] * amount
        self.sales = self.shares_sold[asset] * \
            self.current_price[asset] * (1 - self.commission)
        self.shares_held[asset] -= self.shares_sold[asset]
        self.balance += self.sales
        return True

    def _can_buy(self, amount):
        if self.balance >= self.balance * amount * (1 + self.commission):
            return True
        else:
            return False

    def _buy_or_sell(self, action_type, amount):
        bought = False
        sold = False
        can_buy = self._can_buy(amount=amount)
        for index, asset in enumerate(self.assets_list*2):
            if action_type < index / 2 + 1 and can_buy and not bought:
                bought = self._buy(asset=asset, amount=amount)
            elif action_type < index + 1 and not sold:
                sold = self._sell(asset=asset, amount=amount)

    def _compute_trade(self):
        for asset in self.assets_list:
            if self.shares_sold[asset] > 0 or self.shares_bought[asset] > 0:
                self.trades[asset].append({
                    'step': self.current_step,
                    'amount': self.shares_sold[asset] if self.shares_sold[asset] > 0 else self.shares_bought[asset],
                    'total': self.sales if self.shares_sold[asset] > 0 else self.cost,
                    'type': 'sell' if self.shares_sold[asset] > 0 else 'buy'
                })

    def _compute_net_worth(self):
        self.net_worth = self.balance
        for asset in self.assets_list:
            self.net_worth += self.shares_held[asset] * \
                self.current_price[asset]

    def _compute_buy_n_hold_strategy(self):
        buy_and_hold = 0
        for asset in self.assets_list:
            buy_and_hold += self.initial_bought[asset] * \
                self.current_price[asset]
        self.buy_and_hold = buy_and_hold

    def _take_action(self, action):
        self._compute_current_price()
        action_type = action[0]
        amount = action[1]
        # bounds of action_space doesn't seem to work, so this line is necessary to not overflow actions
        if 0 < amount <= 1 and action_type > 0:
            self._reset_shares_bought_n_sold()
            self._reset_cost_n_sales()
            self._buy_or_sell(action_type=action_type, amount=amount)
            self._compute_trade()

        self._compute_net_worth()
        self._compute_buy_n_hold_strategy()

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
                # ! continuear
                self.visualization = StockTradingGraph(df_complete=self.df_complete)
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
