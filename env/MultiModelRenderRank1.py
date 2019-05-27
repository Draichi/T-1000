"""Render method of trading operations with multi pairs.

This environment use an array rank 1 with 220 items as it's observations space.

Lucas Draichi
2019
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import style
from configs.vars import *

# finance module is no longer part of matplotlib
# see: https://github.com/matplotlib/mpl_finance
# https://matplotlib.org/gallery/pyplots/text_commands.html#sphx-glr-gallery-pyplots-text-commands-py
from mpl_finance import candlestick_ochl as candlestick

style.use('dark_background')

def date2num(date):
    converter = mdates.datestr2num(date)
    return converter


class StockTradingGraph:
    """A stock trading visualization using matplotlib made to render OpenAI gym environments"""

    def __init__(self, df1, df2, df3, render_title):
        self.df1 = df1
        self.df2 = df2
        self.df3 = df3
        self.render_title = render_title
        self.first_coin, self.second_coin, self.thrid_coin = 'BTC', 'ETH', 'LTC'
        self.net_worths = np.zeros(len(df1['Date']))
        self.net_worths[0] = INITIAL_ACCOUNT_BALANCE
        self.buy_and_holds = np.zeros(len(df1['Date']))
        self.buy_and_holds[0] = INITIAL_ACCOUNT_BALANCE

        # Create a figure on screen and set the title
        fig = plt.figure()
        # fig.suptitle('ETHBTC')
        fig.suptitle(self.render_title, fontsize=18)

        # https://matplotlib.org/users/gridspec.html
        # https://matplotlib.org/api/_as_gen/matplotlib.pyplot.subplot2grid.html?highlight=subplot2grid#matplotlib.pyplot.subplot2grid
        self.net_worth_ax = plt.subplot2grid(
            (8, 1), (0, 0), rowspan=2, colspan=1)

        self.price_ax1 = plt.subplot2grid(
            (8, 1), (2, 0), rowspan=2, colspan=1, sharex=self.net_worth_ax)
        self.volume_ax1 = self.price_ax1.twinx()

        self.price_ax2 = plt.subplot2grid(
            (8, 1), (4, 0), rowspan=2, colspan=1, sharex=self.net_worth_ax)
        self.volume_ax2 = self.price_ax2.twinx()

        self.price_ax3 = plt.subplot2grid(
            (8, 1), (6, 0), rowspan=2, colspan=1, sharex=self.net_worth_ax)
        self.volume_ax3 = self.price_ax3.twinx()

        # Add padding to make graph easier to view
        plt.subplots_adjust(left=0.11, bottom=0.24,
                            right=0.90, top=0.90, wspace=0.2, hspace=0)

        # Show the graph without blocking the rest of the program
        plt.show(block=False)

    def _render_net_worth(self, current_step, net_worth, buy_and_hold, shares_held1, shares_held2, shares_held3, balance, step_range, dates):
        # Clear the frame rendered last step
        self.net_worth_ax.clear()
        # set balance and shares held
        self.net_worth_ax.set_title('Holding {:.3f} {} and {:.3f} {} and {:.3f} {} and {:.3f} {}'.format(shares_held1, self.first_coin, shares_held2, self.second_coin, shares_held3, self.thrid_coin, balance, 'USDT'))
        # compute performance
        abs_diff = net_worth - buy_and_hold
        avg = (net_worth + buy_and_hold) / 2
        percentage_diff = abs_diff / avg * 100
        # print performance
        self.net_worth_ax.text(0.95, 0.01, '{0:.2f}%'.format(percentage_diff),
                              verticalalignment='bottom', horizontalalignment='right',
                              transform=self.net_worth_ax.transAxes,
                              color='green' if percentage_diff > 0 else 'red', fontsize=15)

        # Plot net worths
        self.net_worth_ax.plot_date(dates, self.net_worths[step_range], '-', label="Bot's Net Worth", color=BOT_COLOR)
        self.net_worth_ax.plot_date(dates, self.buy_and_holds[step_range], '--', label='Buy and Hold Strategy', color=BUY_N_HOLD_COLOR)
        # Show legend, which uses the label we defined for the plot above
        self.net_worth_ax.legend()
        legend = self.net_worth_ax.legend(loc=2, ncol=2, prop={'size': 8})
        legend.get_frame().set_alpha(0.4)

        last_date = date2num(self.df1['Date'].values[current_step])
        last_net_worth = self.net_worths[current_step]
        last_buy_and_hold = self.buy_and_holds[current_step]

        # Annotate the current net worth on the net worth graph
        self.net_worth_ax.annotate('{0:.2f}'.format(net_worth), (last_date, last_net_worth),
                                   xytext=(last_date, last_net_worth),
                                   bbox=dict(boxstyle='round',
                                             fc='w', ec='k', lw=1),
                                   color="black",
                                   fontsize="small")
        self.net_worth_ax.annotate('{0:.2f}'.format(buy_and_hold), (last_date, last_buy_and_hold),
                                   xytext=(last_date, last_buy_and_hold),
                                   bbox=dict(boxstyle='round',
                                             fc='w', ec='k', lw=1),
                                   color="black",
                                   fontsize="small")

        # Add space above and below min/max net worth
        # self.net_worth_ax.set_ylim(
        #     min(self.net_worths[np.nonzero(self.net_worths)]) / 1.25, max(self.net_worths) * 1.25)
        # self.net_worth_ax.set_ylim(
        #     min(self.buy_and_holds[np.nonzero(self.buy_and_holds)]) / 1.25, max(self.net_worths) * 1.25)

    def _render_price(self, current_step, net_worth, dates, step_range):
        self.price_ax1.clear()
        self.price_ax2.clear()
        self.price_ax3.clear()

        candlesticks1 = zip(dates,
                           self.df1['open'].values[step_range], self.df1['close'].values[step_range],
                           self.df1['high'].values[step_range], self.df1['low'].values[step_range])
        candlesticks2 = zip(dates,
                           self.df2['open'].values[step_range], self.df2['close'].values[step_range],
                           self.df2['high'].values[step_range], self.df2['low'].values[step_range])
        candlesticks3 = zip(dates,
                           self.df3['open'].values[step_range], self.df3['close'].values[step_range],
                           self.df3['high'].values[step_range], self.df3['low'].values[step_range])

        # Plot price using candlestick graph from mpl_finance
        candlestick(self.price_ax1, candlesticks1, width=.04,
                    colorup=UP_COLOR, colordown=DOWN_COLOR)
        candlestick(self.price_ax2, candlesticks2, width=.04,
                    colorup=UP_COLOR, colordown=DOWN_COLOR)
        candlestick(self.price_ax3, candlesticks3, width=.04,
                    colorup=UP_COLOR, colordown=DOWN_COLOR)

        last_date = date2num(self.df1['Date'].values[current_step])
        last_close1 = self.df1['close'].values[current_step]
        last_high1 = self.df1['high'].values[current_step]
        last_close2 = self.df2['close'].values[current_step]
        last_high2 = self.df2['high'].values[current_step]
        last_close3 = self.df3['close'].values[current_step]
        last_high3 = self.df3['high'].values[current_step]

        # Print the current price to the price axis
        self.price_ax1.annotate('{0:.4f}'.format(last_close1), (last_date, last_close1),
                               xytext=(last_date, last_high1),
                               bbox=dict(boxstyle='round',
                                         fc='w', ec='k', lw=1),
                               color="black",
                               fontsize="small")
        self.price_ax2.annotate('{0:.4f}'.format(last_close2), (last_date, last_close2),
                               xytext=(last_date, last_high2),
                               bbox=dict(boxstyle='round',
                                         fc='w', ec='k', lw=1),
                               color="black",
                               fontsize="small")
        self.price_ax3.annotate('{0:.4f}'.format(last_close3), (last_date, last_close3),
                               xytext=(last_date, last_high3),
                               bbox=dict(boxstyle='round',
                                         fc='w', ec='k', lw=1),
                               color="black",
                               fontsize="small")

        # Shift price axis up to give volume chart space
        ylim1 = self.price_ax1.get_ylim()
        ylim2 = self.price_ax2.get_ylim()
        ylim3 = self.price_ax3.get_ylim()

        self.price_ax1.set_ylim(ylim1[0] - (ylim1[1] - ylim1[0])
                               * VOLUME_CHART_HEIGHT, ylim1[1])
        self.price_ax1.set_ylabel('BTC')
        self.price_ax2.set_ylim(ylim2[0] - (ylim2[1] - ylim2[0])
                               * VOLUME_CHART_HEIGHT, ylim2[1])
        self.price_ax2.set_ylabel('ETH')
        self.price_ax3.set_ylim(ylim3[0] - (ylim3[1] - ylim3[0])
                               * VOLUME_CHART_HEIGHT, ylim3[1])
        self.price_ax3.set_ylabel('LTC')


    def _render_volume(self, current_step, net_worth, dates, step_range):
        self.volume_ax1.clear()
        self.volume_ax2.clear()
        self.volume_ax3.clear()

        volume1 = np.array(self.df1['volumefrom'].values[step_range])
        volume2 = np.array(self.df2['volumefrom'].values[step_range])
        volume3 = np.array(self.df3['volumefrom'].values[step_range])

        pos1 = self.df1['open'].values[step_range] - \
            self.df1['close'].values[step_range] < 0
        neg1 = self.df1['open'].values[step_range] - \
            self.df1['close'].values[step_range] > 0
        pos2 = self.df2['open'].values[step_range] - \
            self.df2['close'].values[step_range] < 0
        neg2 = self.df2['open'].values[step_range] - \
            self.df2['close'].values[step_range] > 0
        pos3 = self.df3['open'].values[step_range] - \
            self.df3['close'].values[step_range] < 0
        neg3 = self.df3['open'].values[step_range] - \
            self.df3['close'].values[step_range] > 0

        # Color volume bars based on price direction on that date
        self.volume_ax1.bar(dates[pos1], volume1[pos1], color=UP_COLOR,
                           alpha=0.4, width=.04, align='center')
        self.volume_ax1.bar(dates[neg1], volume1[neg1], color=DOWN_COLOR,
                           alpha=0.4, width=.04, align='center')
        self.volume_ax2.bar(dates[pos2], volume2[pos2], color=UP_COLOR,
                           alpha=0.4, width=.04, align='center')
        self.volume_ax2.bar(dates[neg2], volume2[neg2], color=DOWN_COLOR,
                           alpha=0.4, width=.04, align='center')
        self.volume_ax3.bar(dates[pos3], volume3[pos3], color=UP_COLOR,
                           alpha=0.4, width=.04, align='center')
        self.volume_ax3.bar(dates[neg3], volume3[neg3], color=DOWN_COLOR,
                           alpha=0.4, width=.04, align='center')

        # Cap volume axis height below price chart and hide ticks
        self.volume_ax1.set_ylim(0, max(volume1) / VOLUME_CHART_HEIGHT)
        self.volume_ax1.yaxis.set_ticks([])
        self.volume_ax2.set_ylim(0, max(volume2) / VOLUME_CHART_HEIGHT)
        self.volume_ax2.yaxis.set_ticks([])
        self.volume_ax3.set_ylim(0, max(volume3) / VOLUME_CHART_HEIGHT)
        self.volume_ax3.yaxis.set_ticks([])

    def _render_trades(self, current_step, trades1, trades2, trades3, step_range):
        for trade in trades1:
            if trade['step'] in step_range:
                date = date2num(self.df1['Date'].values[trade['step']])
                high = self.df1['high'].values[trade['step']]
                low = self.df1['low'].values[trade['step']]

                if trade['type'] == 'buy':
                    high_low = low
                    color = UP_TEXT_COLOR
                    marker = '^'
                else:
                    high_low = high
                    color = DOWN_TEXT_COLOR
                    marker = 'v'

                total = '{0:.5f}'.format(trade['total'])
                # print(total)

                # print icon
                self.price_ax1.scatter(date, high_low, color=color, marker=marker, s=50)

                # Print the current price to the price axis
                self.price_ax1.annotate('{} {}'.format(total, 'USDT'),
                                       xy=(date, high_low),
                                       xytext=(date, high_low),
                                       color=color,
                                       fontsize=8)

        for trade in trades2:
            if trade['step'] in step_range:
                date = date2num(self.df1['Date'].values[trade['step']])
                high = self.df2['high'].values[trade['step']]
                low = self.df2['low'].values[trade['step']]

                if trade['type'] == 'buy':
                    high_low = low
                    color = UP_TEXT_COLOR
                    marker = '^'
                else:
                    high_low = high
                    color = DOWN_TEXT_COLOR
                    marker = 'v'

                total = '{0:.5f}'.format(trade['total'])
                # print(total)

                # print icon
                self.price_ax2.scatter(date, high_low, color=color, marker=marker, s=50)

                # Print the current price to the price axis
                self.price_ax2.annotate('{} {}'.format(total, 'USDT'),
                                       xy=(date, high_low),
                                       xytext=(date, high_low),
                                       color=color,
                                       fontsize=8)

        for trade in trades3:
            if trade['step'] in step_range:
                date = date2num(self.df1['Date'].values[trade['step']])
                high = self.df3['high'].values[trade['step']]
                low = self.df3['low'].values[trade['step']]

                if trade['type'] == 'buy':
                    high_low = low
                    color = UP_TEXT_COLOR
                    marker = '^'
                else:
                    high_low = high
                    color = DOWN_TEXT_COLOR
                    marker = 'v'

                total = '{0:.5f}'.format(trade['total'])
                # print(total)

                # print icon
                self.price_ax3.scatter(date, high_low, color=color, marker=marker, s=50)

                # Print the current price to the price axis
                self.price_ax3.annotate('{} {}'.format(total, 'USDT'),
                                       xy=(date, high_low),
                                       xytext=(date, high_low),
                                       color=color,
                                       fontsize=8)

    def render(self, current_step, net_worth, buy_and_hold, trades1, trades2, trades3, shares_held1, shares_held2, shares_held3, balance, window_size):
        self.net_worths[current_step] = net_worth
        self.buy_and_holds[current_step] = buy_and_hold

        window_start = max(current_step - window_size, 0)
        step_range = range(window_start, current_step + 1)

        # Format dates as timestamps, necessary for candlestick graph
        dates = np.array([date2num(x)
                          for x in self.df1['Date'].values[step_range]])

        self._render_net_worth(current_step, net_worth, buy_and_hold, shares_held1, shares_held2, shares_held3, balance, step_range, dates)
        self._render_price(current_step, net_worth, dates, step_range)
        self._render_volume(current_step, net_worth, dates, step_range)
        self._render_trades(current_step, trades1, trades2, trades3, step_range)

        # Format the date ticks to be more easily read
        self.price_ax1.set_xticklabels(self.df1['Date'].values[step_range], rotation=45,
                                      horizontalalignment='right')
        self.price_ax2.set_xticklabels(self.df2['Date'].values[step_range], rotation=45,
                                      horizontalalignment='right')
        self.price_ax3.set_xticklabels(self.df3['Date'].values[step_range], rotation=45,
                                      horizontalalignment='right')

        # Hide duplicate net worth date labels
        plt.setp(self.net_worth_ax.get_xticklabels(), visible=False)
        plt.setp(self.volume_ax1.get_xticklabels(), visible=False)
        plt.setp(self.volume_ax2.get_xticklabels(), visible=False)
        plt.setp(self.price_ax1.get_xticklabels(), visible=False)
        plt.setp(self.price_ax2.get_xticklabels(), visible=False)

        # Necessary to view frames before they are unrendered
        plt.pause(0.001)

    def close(self):
        plt.close()
