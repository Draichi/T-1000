import random
import gym
from gym import spaces
import numpy as np
import colorama
from t_1000.render import GraphGenerator

colorama.init()
WINDOW_SIZE = 40

class TradingEnv(gym.Env):
    visualization = None

    def __init__(self, config):
        self.assets = config['assets'],
        self.assets_list = self.assets[0]
        self.currency_list = config['currency'],
        self.currency = self.currency_list[0]
        self.granularity = config['granularity'],
        self.datapoints = config['datapoints']
        self.df_complete = config['df_complete']
        self.df_features = config['df_features']
        self.initial_balance = config['variables']['initial_account_balance']
        self.commission = config['variables']['commission']
        self.variables = config['variables']
        self.shares_held = {}
        self.shares_bought = {}
        self.shares_sold = {}
        self.first_prices = {}
        self.initial_bought = {}
        self.trades = {}
        self.current_price = {}
        self.observation_length = len(self.df_features[self.assets_list[0]].columns) + 4 + 3 # 4,3 = (balance, cost, sales, net_worth) + (shares bought, shares sold, shares held foreach asset)

        # action space = buy and sell for each asset, pĺus hold position
        action_space = 1 + len(self.assets_list) * 2

        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([action_space, 1]),
            dtype=np.float16)


        # obs space = (num assets, indicator + (balance, cost, sales, net_worth) + (shares bought, shares sold, shares held foreach asset))
        observation_space = (len(self.assets_list),
                             self.observation_length)

        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max,
            high=np.finfo(np.float32).max,
            shape=observation_space,
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

        reward = self.compute_reward()
        done = self.net_worth <= 0 or self.balance <= 0 or self.current_step >= len(
            self.df_features[self.assets_list[0]].loc[:, 'open'].values) - 1
        obs = self._next_observation()

        return obs, reward, done, {}

    def compute_reward(self):
        net_worth_and_buyhold_mean = (self.net_worth + self.buy_and_hold) / 2
        mean = (self.net_worth - self.buy_and_hold) / \
            net_worth_and_buyhold_mean

        reward = self.net_worth - self.initial_balance
        return reward

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
        self.balance = self.initial_balance
        self.net_worth = self.initial_balance
        for asset in self.assets_list:
            self.shares_held[asset] = 0.0
            self.shares_bought[asset] = 0.0
            self.shares_sold[asset] = 0.0

    def _next_observation(self):
        observation = np.empty((0, self.observation_length), int)
        for asset in self.assets_list:
            current_step = np.array(self.df_features[asset].values[self.current_step])
            current_step_with_shares = np.array([np.append(current_step, [
                self.balance,
                self.cost,
                self.sales,
                self.net_worth,
                self.shares_bought[asset],
                self.shares_sold[asset],
                self.shares_held[asset]
            ])])
            observation = np.append(observation, current_step_with_shares, axis=0)
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
        pass
        # profit = self.net_worth - INITIAL_ACCOUNT_BALANCE

        # file = open(filename, 'a+')

        # file.write('Step: {}\n'.format(self.current_step))
        # file.write('Balance: {}\n'.format(self.balance))
        # file.write('Shares held: {}\n'.format(self.shares_held))
        # file.write('Avg cost for held shares: {}\n'.format(self.cost))
        # file.write('Net worth: {}\n'.format(self.net_worth))
        # file.write('Buy and hold strategy: {}\n'.format(self.buy_and_hold))
        # file.write('Profit: {}\n\n'.format(profit))

        # file.close()

    # *--------------------------------------------------------------------
    # * tirar o visualization.render() e trabalhar no rollout.py primeiro?
    # *--------------------------------------------------------------------

    def render(self, mode='live', **kwargs):

        if mode == 'file':
            self._render_to_file(kwargs.get('filename', 'render.txt'))

        elif mode == 'live':
            if self.visualization == None:
                self.visualization = GraphGenerator(assets=self.assets_list, currency=self.currency, granularity=self.granularity[0],
                                                    datapoints=self.datapoints, df_complete=self.df_complete, df_features=self.df_features, variables=self.variables)
            self.visualization.render(current_step=self.current_step, net_worth=self.net_worth, buy_and_hold=self.buy_and_hold,
                                    trades=self.trades, shares_held=self.shares_held, balance=self.balance, window_size=WINDOW_SIZE)

    def close(self):
        if self.visualization != None:
            self.visualization.close()
            self.visualization = None
