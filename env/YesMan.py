"""Gym enrivornment to simulate trading operations with multi pairs.

This environment use an array rank 1 with 220 items as it's observations space.

Lucas Draichi
2019
"""

from env.MultiModelRenderRank1V2 import StockTradingGraph
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

        first_asset_of_list = self.assets[0][0]
        first_df_columns = self.df_features[first_asset_of_list].columns
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
            self.df1_features.loc[:, 'open'].values) - 1
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
        # print('\n', len(observation))
        # print(observation)
        # print('==============\n')
        # quit()/
        return observation

    def _compute_current_price(self):
        for asset in self.assets_list:
            self.current_price[asset] = random.uniform(self.df_features[asset].loc[self.current_step, 'open'],
                                                       self.df_features[asset].loc[self.current_step, 'close'])

    def _take_action(self, action):
        self._compute_current_price()

        action_type = action[0]
        amount = action[1]
#  ! parei aqui

        # bounds of action_space doesn't seem to work, so this line is necessary to not overflow actions
        if 0 < amount <= 1 and action_type > 0:

            self._reset_shares_bought_n_sold()
            self._reset_cost_n_sales()

# ! --
            1 + len(self.assets_list) * 2
# ! --      
            not_bought_yet = True
            not_sold_yet = True
            for index, asset in enumerate(self.assets_list*2):
                # buy
                if action_type < index / 2 + 1 and self.balance >= self.balance * amount * (1 + self.commission) and not_bought_yet:
                    self.shares_bought[asset] = self.balance * amount / self.current_price[asset]
                    self.cost = self.shares_bought[asset] * self.current_price[asset] * (1 + self.commission)
                    self.shares_held[asset] += self.shares_bought[asset]
                    self.balance -= self.cost
                    not_bought_yet = False
                # sell
                elif action_type < index + 1 and not_sold_yet:
                    self.shares_sold[asset] = self.shares_held * amount
                    self.sales = self.shares_sold[asset] * self.current_price[asset] * (1 - self.commission)
                    self.shares_held[asset] -= self.shares_sold[asset]
                    self.balance += self.sales
                    not_sold_yet = False
# ? revisar esse codigo acima
            # buy shares1
            # check if has enough money to trade
            if action_type < 1 and self.balance >= self.balance * amount * (1 + self.commission):
                self.shares1_bought = self.balance * amount / current_price1
                self.cost = self.shares1_bought * \
                    current_price1 * (1 + self.commission)
                self.shares1_held += self.shares1_bought
                self.balance -= self.cost
            # sell shares1
            elif action_type < 2:
                self.shares1_sold = self.shares1_held * amount
                self.sales = self.shares1_sold * \
                    current_price1 * (1 - self.commission)
                self.shares1_held -= self.shares1_sold
                self.balance += self.sales

            # buy shares 2
            # check if has enough money to trade
            elif action_type < 3 and self.balance >= self.balance * amount * (1 + self.commission):
                self.shares2_bought = self.balance * amount / current_price2
                self.cost = self.shares2_bought * \
                    current_price2 * (1 + self.commission)
                self.shares2_held += self.shares2_bought
                self.balance -= self.cost
            # sell shares 2
            elif action_type < 4:
                self.shares2_sold = self.shares2_held * amount
                self.sales = self.shares2_sold * \
                    current_price2 * (1 - self.commission)
                self.shares2_held -= self.shares2_sold
                self.balance += self.sales

            # buy shares 3
            # check if has enough money to trade
            elif action_type < 5 and self.balance >= self.balance * amount * (1 + self.commission):
                self.shares3_bought = self.balance * amount / current_price3
                self.cost = self.shares3_bought * \
                    current_price3 * (1 + self.commission)
                self.shares3_held += self.shares3_bought
                self.balance -= self.cost
            # sell shares 3
            elif action_type < 6:
                self.shares3_sold = self.shares3_held * amount
                self.sales = self.shares3_sold * \
                    current_price3 * (1 - self.commission)
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

        self.net_worth = self.balance + (self.shares1_held * current_price1) + (
            self.shares2_held * current_price2) + (self.shares3_held * current_price3)
        self.buy_and_hold = self.initial_bought1 * current_price1 + \
            self.initial_bought2 * current_price2 + self.initial_bought3 * current_price3

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
