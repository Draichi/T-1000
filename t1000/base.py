"""
t1000 base module.

This is the principal module of the t1000_v2 project.
here you put your main classes and objects.
"""


from .brain import Brain
from .exchange_environment import ExchangeEnvironment

CONFIG_SPEC_CONSTANTS = {
    "candlestick_width": {  # constants
        "day": 1,
        "hour": 0.04,
        "minute": 0.0006
    },
}


class Renderer:
    def __init__(self) -> None:
        pass


class TradingFloor(ExchangeEnvironment, Brain, Renderer):
    """A class containing all the logic and instruments to simulate a trading operation.

    documentation example: https://www.programiz.com/python-programming/docstrings

    ...

    Attributes
    ----------

    assets : list
        a list of assets available to trade.
    checkpoint_path : str
        a path to a saved model checkpoint, useful if you want to resume training from a already trained model (default '').
    algorithm : 

    Methods
    -------

    create_trial_name()
        Return the formatted trial name as a string

    """

    def __init__(self, assets: list[str], checkpoint_path='', algorithm='PPO', currency='USD', granularity='hour', data_points=150, initial_balance=300, exchange_commission=0.00075, exchange='CCCAGG') -> None:
        ExchangeEnvironment.__init__(
            self, net_worth=initial_balance, assets=assets, currency=currency, exchange=exchange, granularity=granularity, data_points=data_points, balance=initial_balance, exchange_commission=exchange_commission)
        Brain.__init__(self, 1e-4)
        Renderer.__init__(self)
        self.assets = assets
        self.algorithm = algorithm
        self.currency = currency
        self.granularity = granularity
        self.data_points = data_points
        self.config_spec = {}

    def generate_config_spec(self):
        pass

    def add_data_frames_to_config_spec(self):
        pass

    def check_variables_integrity(self) -> None:
        if type(self.assets) != list or len(self.assets) == 0:
            raise ValueError("Incorrect 'assets' value")
        if type(self.currency) != str:
            raise ValueError("Incorrect 'currency' value")
        if type(self.granularity) != str:
            raise ValueError("Incorrect 'granularity' value")
        if type(self.data_points) != int or 1 > self.data_points > 2000:
            raise ValueError("Incorrect 'data_points' value")
