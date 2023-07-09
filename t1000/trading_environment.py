import gymnasium as gym
import numpy as np
import random
from gymnasium import spaces
from ray.rllib.env.env_context import EnvContext


class TradingEnvironment(gym.Env):
    def __init__(self, config: EnvContext):

        self.current_step: int = 0
        self.df_features = config['df_features']
        
        self.exchange_commission = 0.00075
        initial_balance = 1000
        self._net_worth = initial_balance
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.cost: float = 0
        self.sales: float = 0
        self.shares_bought: float = 0
        self.shares_sold: float = 0
        self.shares_held: float = 0
        self.initial_bought = 0
        self.trades: list = []

        # 4,3 = (balance, cost, sales, net_worth) + (shares bought, shares sold, shares held)
        self.observation_length = len(
            self.df_features.columns) + 4 + 3
        
        print('observation length',self.observation_length)

        # action space = buy and sell and hold position
        action_space = 3


        self.action_space = spaces.Box(
            low=np.array([0, 0]),
            high=np.array([action_space, 1]),
            dtype=np.float16)

        self.observation_space = spaces.Box(
            low=-np.finfo(np.float32).max,
            high=np.finfo(np.float32).max,
            shape=(self.observation_length,),
            dtype=np.float16)

    
    @property
    def net_worth(self) -> float:
        """Returns the foo var"""
        return self._net_worth

    @net_worth.setter
    def net_worth(self, value: float):
        self._net_worth = value

    def __reset_net_worth(self):
        self.net_worth = self.initial_balance

    def __reset_all_shares(self):
        self.shares_bought = 0
        self.shares = 0
        self.shares = 0

    def _compute_current_price(self):
        self.current_price = random.uniform(
            self.df_features.loc[self.current_step, 'open'],
            self.df_features.loc[self.current_step, 'close'])

    def __buy(self, amount: float):
        self.shares_bought = self.balance * \
            amount / self.current_price

        self.cost = self.shares_bought * \
            self.current_price * \
            (1 + self.exchange_commission)

        self.shares_held += self.shares_bought

        self.balance -= self.cost

    def __sell(self, amount: float):
        self.shares_sold = self.shares_held * amount

        self.sales = self.shares_sold * \
            self.current_price * \
            (1 + self.exchange_commission)

        self.shares_held -= self.shares_sold

        self.balance += self.sales

    def __amount_can_be_spent(self, amount: float) -> bool:
        """Calculate if has balance to spend"""
        if self.balance >= self.balance * amount * (1 + self.exchange_commission):
            return True
        else:
            return False

    def reset_shares_bought_and_sold(self):
        self.shares_bought = 0
        self.shares_sold = 0

    def reset_balance(self):
        self.balance = self.initial_balance
        self.reset_cost_and_sales()
        self.__reset_net_worth()
        self.__reset_all_shares()

    def reset_trades(self):
        self.trades = []

    def reset_cost_and_sales(self):
        self.cost = 0
        self.sales = 0

    def _get_first_price(self):
            self.first_price = self.df_features['close'][0]

    def trade(self, action_type: float, action_strength: float):
        """Check if it's possible to buy or sell"""
        is_bought = False
        is_sold = False
        is_possible_to_buy = self.__amount_can_be_spent(amount=action_strength)
        if action_type < 1 and is_possible_to_buy and not is_bought:
            is_bought = True
            self.__buy(amount=action_strength)
        elif action_type < 2 and not is_sold:
            is_sold = True
            self.__sell(amount=action_strength)

    def __compute_initial_bought(self):
        """spread the initial account balance through all assets"""

        self.__buy(amount=self.initial_balance / 2)
    
    def __get_next_observation(self):
        empty_observation_array = np.empty((0, self.observation_length), int)
        current_market_state = np.array(
            self.df_features.values[self.current_step])
        current_state = np.array([np.append(current_market_state, [
            self.balance,
            self.cost,
            self.sales,
            self.net_worth,
            self.shares_bought,
            self.shares_sold,
            self.shares_held
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
        print('\nself.observation_space.sample():',self.observation_space.sample())
        self.reset_balance()
        self.reset_trades()
        print("Resetting environment")
        # TODO
        self._get_first_price()
        self.__compute_initial_bought()

        return self.__get_next_observation()

    def close(self):
        pass
