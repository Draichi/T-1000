import gym
import numpy as np
from gym import spaces


from .wallet import Wallet


class ExchangeEnvironment(Wallet, gym.Env):
    def __init__(self, net_worth: int, balance: int, assets: list, currency: str,
                 exchange: str, granularity: str, data_points: int, exchange_commission: float) -> None:

        Wallet.__init__(self, net_worth=net_worth,
                        balance=balance, assets=assets, exchange_commission=exchange_commission, exchange=exchange, granularity=granularity, data_points=data_points, currency=currency)

        self.current_step: int = 0
        # 4,3 = (balance, cost, sales, net_worth) + (shares bought, shares sold, shares held foreach asset)
        self.observation_length = len(
            self.df_features[assets[0]].columns) + 4 + 3

        # action space = buy and sell for each asset, plus hold position
        action_space = 1 + len(assets) * 2

        # obs space = (num assets, indicator + (balance, cost, sales, net_worth) + (shares bought, shares sold, shares held foreach asset))
        observation_space = (len(assets),
                             self.observation_length)

        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([action_space, 1]),
            dtype=np.float16)

        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max,
            high=np.finfo(np.float32).max,
            shape=observation_space,
            dtype=np.float16)

    def __compute_initial_bought(self):
        """spread the initial account balance through all assets"""
        for asset in self.assets:
            self.initial_bought[asset] = 1/len(self.assets) * \
                self.initial_balance / self.first_prices[asset]

    def __get_next_observation(self):
        empty_observation_array = np.empty((0, self.observation_length), int)
        for asset in self.assets:
            current_market_state = np.array(
                self.df_features[asset].values[self.current_step])
            current_state = np.array([np.append(current_market_state, [
                self.balance,
                self.cost,
                self.sales,
                self.net_worth,
                self.shares_bought_per_asset[asset],
                self.shares_sold_per_asset[asset],
                self.shares_held_per_asset[asset]
            ])])
            next_observation = np.append(
                empty_observation_array, current_state, axis=0)

            return next_observation

    def __take_action(self, action: list[float]):
        """Take an action within the environment"""
        action_type = action[0]
        action_strength = action[1]
        # TODO
        # - compute_current_price()

        """bounds of action_space doesn't seem to work, so this line is necessary to not overflow actions"""
        if 0 < action_strength <= 1 and action_type > 0:
            # TODO
            # - reset_shares_bought_n_sold()
            # - reset_cost_n_sales()
            # - buy_or_sell(action_type=action_type, amount=amount)
            # - compute_trade()
            self.reset_shares_bought_and_sold()
            self.reset_cost_and_sales()

    def get_HODL_strategy(self) -> None:
        pass

    def compute_reward(self) -> None:
        pass

    def step(self, action: list[float]):
        """Execute one time step within the environment"""
        # TODO
        self.__take_action(action)
        self.current_step += 1

    def reset(self):
        """Reset the ExchangeEnvironment to it's initial state"""
        self.current_step = 0
        self.reset_balance()
        self.reset_trades()
        # TODO
        # - get_first_prices

        return self.__get_next_observation()

    def close(self):
        pass
