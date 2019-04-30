"""Simple gym env implemented by Lucas Draichi to simulate
a single pair trading process.

Inpired by cart-pole system implemented by Rich Sutton et al.
Copied from http://incompleteideas.net/sutton/book/code/pole.c
permalink: https://perma.cc/C9ZM-652R

Lucas Draichi 2019
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import gym
from gym.spaces import Discrete, Box
from configs.vars import WALLET_FIRST_SYMBOL, WALLET_SECOND_SYMBOL, FEES

plt.style.use('dark_background')
mpl.rcParams.update(
    {
        "font.size": 15,
        "axes.labelsize": 15,
        "lines.linewidth": 1,
        "lines.markersize": 8
    }
)

class SinglePairTradingEnv(gym.Env):

    def __init__(self, config):
        self.keys = config['keys']
        self.symbol_list = config['symbols']
        self.first_coin = config['first_coin']
        self.second_coin = config['second_coin']
        self.index = 0
        self._first_render = True
        self._spread_coefficients = [1]
        self.dicount_rate = 1 - FEES
        self.wallet_first_symbol = WALLET_FIRST_SYMBOL
        self.wallet_second_symbol = WALLET_SECOND_SYMBOL
        self.actual_price = 1.0
        self.portfolio_value = 1.0
        self.action_space = Discrete(3)
        self.action = 3
        self.observation_space = Box(
            low=-np.finfo(np.float32).max, high=np.finfo(np.float32).max,
            shape=(len(self.keys), ), dtype=np.float32
        ) # shape=(number of columns,)

    def reset(self):
        self.index = 0
        self.wallet_first_symbol = WALLET_FIRST_SYMBOL
        self.wallet_second_symbol = WALLET_SECOND_SYMBOL
        self.portfolio_value = 1.0
        state = self.symbol_list[self.index]
        return state

    def step(self, action):
        if action not in [0,1,2]:
            raise AssertionError()
        self.action = action
        price_index = list(self.keys).index('close')
        wallet_first_symbol_index = list(self.keys).index('wallet_first_symbol')
        wallet_second_symbol_index = list(self.keys).index('wallet_second_symbol')
        observable_state = self.symbol_list[self.index]
        price_before_action = observable_state[price_index]
        # self.actual_price = price_before_action

        total_portfolio_value_before_action = (self.wallet_first_symbol * price_before_action) + self.wallet_second_symbol

        if action == 0: # buy
            self.wallet_first_symbol -= price_before_action
            self.wallet_second_symbol += price_before_action
        elif action == 1: # sell
            self.wallet_first_symbol += price_before_action
            self.wallet_second_symbol -= price_before_action

        self.index += 1
        next_observable_state = self.symbol_list[self.index]

        price_after_action = next_observable_state[price_index]

        self.portfolio_value = (self.wallet_first_symbol * price_after_action) + self.wallet_second_symbol

        total_portfolio_value_after_action = self.dicount_rate * self.portfolio_value

        reward = total_portfolio_value_after_action - total_portfolio_value_before_action

        next_observable_state[wallet_first_symbol_index] = self.wallet_first_symbol
        next_observable_state[wallet_second_symbol_index] = self.wallet_second_symbol

        done = self.index >= len(self.symbol_list)-1

        return next_observable_state, reward, done, {}

    def _handle_close(self, evt):
        self._closed_plot = True

    def render(self, savefig=False, filename='myfig'):

        if self._first_render:
            self._f, self._ax = plt.subplots(
                len(self._spread_coefficients) + int(len(self._spread_coefficients) > 1),
                sharex=True
            )
            if len(self._spread_coefficients) == 1:
                self._ax = [self._ax]
            self._f.set_size_inches(12, 6)
            self._first_render = False
            self._f.canvas.mpl_connect('close_event', self._handle_close)
        # if len(self._spread_coefficients) > 1:
        #     for prod_i in range(len(self._spread_coefficients)):
        #         bid = self._prices_history[-1][2 * prod_i]
        #         ask = self._prices_history[-1][2 * prod_i + 1]
        #         self._ax[prod_i].plot([self.index, self.index + 1],
        #                               [bid, bid], color='white')
        #         self._ax[prod_i].plot([self.index, self.index + 1],
        #                               [ask, ask], color='white')
        #         self._ax[prod_i].set_title('Product {} (spread coef {})'.format(
        #             prod_i, str(self._spread_coefficients[prod_i])))

        price_btc_index = list(self.keys).index('close')
        observable_state = self.symbol_list[self.index]
        price_btc_before_action = observable_state[price_btc_index]
        # Spread price
        prices = price_btc_before_action
        # bid, ask = calc_spread(prices, self._spread_coefficients)
        self._ax[-1].plot([self.index, self.index + 1],
                          [prices, prices], color='white')
        # self._ax[-1].plot([self.index, self.index + 1],
        #                   [prices, prices], color='white')
        ymin, ymax = self._ax[-1].get_ylim()
        yrange = ymax - ymin
        if self.action == 1: #sell
            self._ax[-1].scatter(self.index + 0.5, prices + 0.03 *
                                 yrange, color='orangered', marker='v')
        elif self.action == 0: #buy
            self._ax[-1].scatter(self.index + 0.5, prices - 0.03 *
                                 yrange, color='lawngreen', marker='^')
        # plt.suptitle('Cumulated Reward: ' + "%.2f" % self._total_reward + ' ~ ' +
        #              'Cumulated PnL: ' + "%.2f" % self._total_pnl + ' ~ ' +
        #              'Position: ' + ['flat', 'long', 'short'][list(self._position).index(1)] + ' ~ ' +
        #              'Entry Price: ' + "%.2f" % self._entry_price)
        plt.suptitle('Portfolio Value: {} {}'.format(self.portfolio_value, self.second_coin))
        self._f.tight_layout()
        plt.xticks(range(self.index)[::5])
        plt.xlim([max(0, self.index - 80.5), self.index + 0.5])
        plt.subplots_adjust(top=0.85)
        plt.pause(0.01)
        if savefig:
            plt.savefig(filename)