from configs.functions import get_datasets

class Trade:
    """Fertile environment to trade cryptos via algorithm"""

    def __init__(self, assets=['BTC','LTC','ETH'], currency='USDT', granularity='day', datapoints=600):
        """Create a trade environment

        Arguments:
            assets {list} -- List of crypto symbols
            currency {str} -- To form the pair e.g. BTC/USDT ETH/USDT LTC/USDT
            granularity {str} -- 'day' / 'hour' / 'minute'
            datapoints {str} -- Number of tickers [1-2000]
            algo {str} -- 'PPO' (Proximal Policy Optimization), 'APPO' (Asynchronous Proximal Policy Optimization), 'DQN' (Deep Q-Network)
        """
        self.assets = assets
        self.currency = currency
        self.granularity = granularity
        self.datapoints = datapoints
        self.df = {}
        self.populate_dfs()

    def populate_dfs(self):
        if type(self.assets) != list or len(self.assets) == 0:
            raise ValueError("Incorrect 'assets' value")
        for asset in self.assets:
            df_train = asset + '_train'
            df_rollout = asset + '_rollout'
            self.df[df_train], self.df[df_rollout] = get_datasets(asset=asset,
                                                                  currency=self.currency,
                                                                  granularity=self.granularity,
                                                                  datapoints=self.datapoints)
    def train(self, algo='PPO', timesteps=3e10, checkpoint_freq=100, lr_schedule=[[[0, 7e-5], [3e10, 7e-6]]]):
        # print(self.df)
        pass
