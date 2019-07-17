from configs.functions import get_datasets

class Trade:
    """Fertile environment to trade cryptos via algorithm"""

    def __init__(self, assets=['BTC','LTC','ETH'], currency='USDT', granularity='day', datapoints=600, algo='PPO'):
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
        self.algo = algo
        self.df = {}

        for asset in self.assets:
            df_train = asset + '_train'
            df_rollout = asset + '_rollout'
            self.df[df_train], self.df[df_rollout] = get_datasets(asset=asset,
                                                                  currency=self.currency,
                                                                  granularity=self.granularity,
                                                                  datapoints=self.datapoints)

    def train(self):
        print(self.df)
