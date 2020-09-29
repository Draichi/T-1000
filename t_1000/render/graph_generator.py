import numpy as np
import pandas as pd
from tabulate import tabulate
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import style

from mpl_finance import candlestick_ochl as candlestick

style.use('dark_background')

# BALANCE_COLOR = ['#ffa929', '#ff297f', '#7fff29', '#297fff']
BUY_N_HOLD_COLOR = '#297fff'
BOT_COLOR = '#ffaa00'
BALANCE_COLOR = '#44a769'
UP_COLOR = '#297FFF'
DOWN_COLOR = '#FFAA00'
VOLUME_CHART_HEIGHT = 0.33
UP_TEXT_COLOR = '#00b909'
DOWN_TEXT_COLOR = '#c60606'


def date2num(date):
    converter = mdates.datestr2num(date)
    return converter


class GraphGenerator:
    """A stock trading visualization using matplotlib made to render OpenAI gym environments"""

    def __init__(self, assets, currency, granularity, datapoints, df_complete, df_features, variables):
        self.assets = assets
        self.currency = currency
        self.granularity = granularity
        self.datapoints = datapoints
        self.df_complete = df_complete
        self.df_features = df_features
        self.variables = variables
        self.candlestick_width = variables['candlestick_width'].get(
            granularity, 1)
        self.date_values = self.df_complete[self.assets[0]]['Date'].values

        # ? benchmark strats
        self.buy_and_holds = np.zeros(len(df_complete[assets[0]]['Date']))
        self.net_worths = np.zeros(len(df_complete[assets[0]]['Date']))

        self.buy_and_holds[0] = variables['initial_account_balance']
        self.net_worths[0] = variables['initial_account_balance']

        fig = plt.figure()
        fig.suptitle('T-1000', fontsize=18)

        self.price_axs = {}
        self.volume_axs = {}
        rowspan = len(assets)
        colspan = 4  # ! idk
        canvas_x_size = len(assets) * rowspan
        canvas_y_size = len(assets) + 2  # ? + balance and net_worth

        self.net_worth_ax = plt.subplot2grid(
            (canvas_x_size, canvas_y_size), (0, colspan), rowspan=4, colspan=1)
        self.net_worth_ax.yaxis.tick_right()

        self.balance_ax = plt.subplot2grid(
            (canvas_x_size, canvas_y_size), (5, colspan), rowspan=4, colspan=1)
        self.balance_ax.yaxis.tick_right()

        for index, asset in enumerate(assets):
            self.price_axs[asset] = plt.subplot2grid((canvas_x_size, canvas_y_size), (len(
                assets) * index, 0), rowspan=rowspan, colspan=colspan)
            self.volume_axs[asset] = self.price_axs[asset].twinx()
            self.price_axs[asset].yaxis.tick_right()

        plt.subplots_adjust(left=0.11, bottom=0.24,
                            right=0.90, top=0.90, wspace=0.2, hspace=0)

        # ? Show the graph without blocking the rest of the program
        plt.show(block=False)

    def _render_net_worth(self, current_step, net_worth, buy_and_hold, step_range, dates):
        # Clear the frame rendered last step
        self.net_worth_ax.clear()
        # compute performance
        abs_diff = net_worth - buy_and_hold
        avg = (net_worth + buy_and_hold) / 2
        percentage_diff = abs_diff / avg * 100
        # print performance
        self.net_worth_ax.text(0.95, 0.01, '{0:.2f}%'.format(percentage_diff),
                               verticalalignment='bottom',
                               horizontalalignment='right',
                               transform=self.net_worth_ax.transAxes,
                               color='green' if percentage_diff > 0 else 'red', fontsize=15)
        x = np.arange(2)
        y = [buy_and_hold, net_worth]
        self.net_worth_ax.bar(x, y, color=[BUY_N_HOLD_COLOR, BOT_COLOR])
        self.net_worth_ax.set_title(
            "Net Worth ({})".format(self.currency))
        self.net_worth_ax.set_xticklabels(('', 'HODL', '', 'T-1000'))

        # Annotate the current net worth on the net worth graph
        self.net_worth_ax.annotate("{0:.2f}".format(buy_and_hold),
                                   xy=(0, buy_and_hold),
                                   xytext=(0, buy_and_hold),
                                   bbox=dict(boxstyle='round',
                                             fc='w', ec='k', lw=1),
                                   color="black",
                                   fontsize="small")
        self.net_worth_ax.annotate("{0:.2f}".format(net_worth),
                                   xy=(1, net_worth),
                                   xytext=(1, net_worth),
                                   bbox=dict(boxstyle='round',
                                             fc='w', ec='k', lw=1),
                                   color="black",
                                   fontsize="small")

    def _render_balance(self, shares_held, balance):
        # Clear the frame rendered last step
        self.balance_ax.clear()
        x = np.arange(len(self.assets) + 1)
        y = [shares_held[asset] for asset in self.assets]
        y.append(balance)
        self.balance_ax.bar(x, y, color=BALANCE_COLOR)
        self.balance_ax.set_title("Balance")
        labels = ('',)
        for asset in self.assets:
            labels += (asset, )
        labels += (self.currency, )
        self.balance_ax.set_xticklabels(labels)

        for index, asset in enumerate(self.assets):
            self.balance_ax.annotate("{0:.3f}".format(shares_held[asset]), xy=(index, shares_held[asset]), xytext=(
                index, shares_held[asset]), bbox=dict(boxstyle='round', fc='w', ec='k', lw=1), color='black', fontsize='small')
        self.balance_ax.annotate("{0:.3f}".format(balance),
                                 xy=(len(self.assets), balance),
                                 xytext=(len(self.assets), balance),
                                 bbox=dict(boxstyle='round',
                                           fc='w', ec='k', lw=1),
                                 color="black",
                                 fontsize="small")

    def _render_price(self, current_step, net_worth, dates, step_range):
        candlesticks = {}
        last_dates = {}
        last_closes = {}
        last_highs = {}
        y_limit = {}
        for index, asset in enumerate(self.assets):
            if index == 0:
                self.price_axs[asset].set_title(
                    'Candlesticks')  # ? this can go out?
            self.price_axs[asset].clear()
            candlesticks[asset] = zip(dates,
                                      self.df_features[asset]['open'].values[step_range],
                                      self.df_features[asset]['close'].values[step_range],
                                      self.df_features[asset]['high'].values[step_range],
                                      self.df_features[asset]['low'].values[step_range])
            candlestick(self.price_axs[asset],
                        candlesticks[asset],
                        width=self.candlestick_width,
                        colorup=UP_COLOR,
                        colordown=DOWN_COLOR)
            last_dates[asset] = date2num(
                self.df_complete[asset]['Date'].values[current_step])
            last_closes[asset] = self.df_features[asset]['close'].values[current_step]
            last_highs[asset] = self.df_features[asset]['high'].values[current_step]
            self.price_axs[asset].annotate(s="{0:.4f}".format(last_closes[asset]), xy=(
                last_dates[asset], last_closes[asset]), xytext=(last_dates[asset], last_highs[asset]), bbox=dict(boxstyle='round', fc='w', ec='k', lw=1), color='black', fontsize='small')
            y_limit[asset] = self.price_axs[asset].get_ylim()
            self.price_axs[asset].set_ylim(y_limit[asset][0] - (
                y_limit[asset][1] - y_limit[asset][0]) * VOLUME_CHART_HEIGHT, y_limit[asset][1])
            self.price_axs[asset].set_ylabel(
                '{}/{}'.format(asset, self.currency))

    def _render_volume(self, current_step, net_worth, dates, step_range):
        volumes = {}
        pos = {}
        neg = {}
        for asset in self.assets:
            self.volume_axs[asset].clear()
            volumes[asset] = np.array(self.df_complete[asset]['volumefrom'].values[step_range])
            pos[asset] = self.df_complete[asset]['open'].values[step_range] - self.df_complete[asset]['close'].values[step_range] < 0
            neg[asset] = self.df_complete[asset]['open'].values[step_range] - self.df_complete[asset]['close'].values[step_range] > 0
            self.volume_axs[asset].bar(dates[pos[asset]], volumes[asset][pos[asset]], color=UP_COLOR, alpha=0.4, width=self.candlestick_width, align='center')
            self.volume_axs[asset].bar(dates[neg[asset]], volumes[asset][neg[asset]], color=DOWN_COLOR, alpha=0.4, width=self.candlestick_width, align='center')
            # > Cap volume axis height below price chart and hide ticks
            self.volume_axs[asset].set_ylim(0, max(volumes[asset]) / VOLUME_CHART_HEIGHT)
            self.volume_axs[asset].yaxis.set_ticks([])

    def _render_trades(self, current_step, trades, step_range):
        for asset in self.assets:
            for trade in trades[asset]:
                if trade['step'] in step_range:
                    date = date2num(self.df_complete[asset]['Date'].values[trade['step']])
                    high = self.df_complete[asset]['high'].values[trade['step']]
                    low = self.df_complete[asset]['low'].values[trade['step']]
                    if trade['type'] == 'buy':
                        high_low = low
                        color = UP_TEXT_COLOR
                        marker = '^'
                    else:
                        high_low = high
                        color = DOWN_TEXT_COLOR
                        marker = 'v'
                    total = '{0:.5f}'.format(trade['total'])
                    self.price_axs[asset].scatter(date, high_low, color=color, marker=marker, s=50)
                    self.price_axs[asset].annotate('{} {}'.format(total, self.currency), xy=(date, high_low), xytext=(date, high_low), color=color, fontsize=8)

    def _print_trades_overview(self, balance, net_worth, shares_held, trades, buy_and_hold):
        print('\nTrades')
        for asset in self.assets:
            df = pd.DataFrame(trades[asset])
            if 'step' in df.columns.tolist():
                df['Date'] = self.df_complete[asset]['Date'].values[df['step'] -1]
                df['total ({})'.format(self.currency)] = df['total']
                df.set_index('Date', inplace=True)
                df.drop(['step', 'total'], axis=1, inplace=True)
                x = tabulate(df, headers='keys', tablefmt='psql')
                print(asset)
                print(x)
        shares_held[self.currency] = balance
        df_shares_held = pd.DataFrame(shares_held, index=[0])
        x_shares = tabulate(df_shares_held, headers='keys', tablefmt='psql')
        print('\nPortfolio')
        print(x_shares)
        print('Net Worth:', net_worth, self.currency)
        print('Buy \'n hold:', buy_and_hold, self.currency)
        print('\n')

    def render(self, current_step, net_worth, buy_and_hold, trades, shares_held, balance, window_size):
        self.net_worths[current_step] = net_worth
        self.buy_and_holds[current_step] = buy_and_hold

        window_start = max(current_step - window_size, 0)
        step_range = range(window_start, current_step + 1)

        # Format dates as timestamps, necessary for candlestick graph
        dates = np.array([date2num(x)
                          for x in self.df_complete[self.assets[0]]['Date'].values[step_range]])

        self._render_net_worth(current_step, net_worth,
                               buy_and_hold, step_range, dates)

        self._render_balance(shares_held, balance)
        self._render_price(current_step, net_worth, dates, step_range)
        self._render_volume(current_step, net_worth, dates, step_range)
        self._render_trades(current_step, trades, step_range)

        # Format the date ticks to be more easily read
        last_asset_index = len(self.assets) - 1
        for index, asset in enumerate(self.assets):
            self.price_axs[asset].set_xticklabels(
                self.df_complete[asset]['Date'].values[step_range], rotation=45, horizontalalignment='right')

        # Hide duplicate net worth date labels
            if not index == last_asset_index:
                plt.setp(
                    self.volume_axs[asset].get_xticklabels(), visible=False)
                plt.setp(
                    self.price_axs[asset].get_xticklabels(), visible=False)

        # Necessary to view frames before they are unrendered
        plt.pause(0.001)

        # print trades info on console
        last_step = current_step >= len(self.date_values) - 1
        if last_step:
            self._print_trades_overview(balance, net_worth, shares_held, trades, buy_and_hold)

    def close(self):
        plt.close()
