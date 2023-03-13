from .market import Market


class Wallet(Market):
    def __init__(self, net_worth: float, balance: float, assets: list[str], exchange_commission: float, exchange: str, currency: str, data_points: int, granularity: str) -> None:

        Market.__init__(self, exchange=exchange, assets=assets, currency=currency,
                        data_points=data_points, granularity=granularity)

        self.exchange_commission = exchange_commission
        self._net_worth = net_worth
        self.initial_balance = balance
        self.balance = balance
        self.cost: float = 0
        self.sales: float = 0
        self.shares_bought_per_asset: dict[str, float] = {}
        self.shares_sold_per_asset: dict[str, float] = {}
        self.shares_held_per_asset: dict[str, float] = {}
        self.initial_bought = {}
        self.trades: dict[str, list] = {}
        self.assets: list[str] = assets

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
        for asset in self.assets:
            self.shares_bought_per_asset[asset] = 0
            self.shares_held_per_asset[asset] = 0
            self.shares_sold_per_asset[asset] = 0

    def __buy(self, asset: str, amount: float) -> bool:
        self.shares_bought_per_asset[asset] = self.balance * \
            amount / self.current_price_per_asset[asset]

        self.cost = self.shares_bought_per_asset[asset] * \
            self.current_price_per_asset[asset] * \
            (1 + self.exchange_commission)

        self.shares_held_per_asset[asset] += self.shares_bought_per_asset[asset]

        self.balance -= self.cost

        return True

    def __sell(self, asset: str, amount: float) -> bool:
        self.shares_sold_per_asset[asset] = self.shares_held_per_asset[asset] * amount

        self.sales = self.shares_sold_per_asset[asset] * \
            self.current_price_per_asset[asset] * \
            (1 + self.exchange_commission)

        self.shares_held_per_asset[asset] -= self.shares_sold_per_asset[asset]

        self.balance += self.sales

        return True

    def __amount_can_be_spent(self, amount: float) -> bool:
        """Calculate if has balance to spend"""
        if self.balance >= self.balance * amount * (1 + self.exchange_commission):
            return True
        else:
            return False

    def reset_shares_bought_and_sold(self):
        for asset in self.assets:
            self.shares_bought_per_asset[asset] = 0
            self.shares_sold_per_asset[asset] = 0

    def reset_balance(self):
        self.balance = self.initial_balance
        self.reset_cost_and_sales()
        self.__reset_net_worth()
        self.__reset_all_shares()

    def reset_trades(self):
        for asset in self.assets:
            self.trades[asset] = []

    def reset_cost_and_sales(self):
        self.cost = 0
        self.sales = 0

    def trade(self, action_type: float, action_strength: float):
        """Check if it's possible to buy or sell"""
        is_bought = False
        is_sold = False
        is_possible_to_buy = self.__amount_can_be_spent(amount=action_strength)
        for index, asset in enumerate(self.assets * 2):
            if action_type < index / 2 + 1 and is_possible_to_buy and not is_bought:
                is_bought = True
            elif action_type < index + 1 and not is_sold:
                is_sold = True
