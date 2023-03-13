import os

import pandas as pd
import requests
from dotenv import load_dotenv
from ray import data as ray_data
from ta import add_all_ta_features


class Market:
    """An abstraction of a crypto market

    Attributes
    ----------
        - exchange (str): the exchange name.
        - assets (list[str]): a list containing assets to trade. Example: `["BTC", "XMR"]`
        - granularity (str): how to fetch the data. Options: `hour`, `day`."""
    load_dotenv()
    CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY')
    PATH_TO_COMPLETE_DATA_FRAME = 't1000/data/complete_{}_data_frame.csv'

    def __init__(self, exchange: str, assets: list[str], granularity: str, currency: str, data_points: int) -> None:
        self.df_features = {}
        self.data_frames: dict[str, pd.DataFrame] = {}
        self.train_data_frame = {}
        self.test_data_frame = {}
        self.first_prices: dict[str, float] = {}
        self.exchange = exchange
        self.granularity = granularity
        self.currency = currency
        self.data_points = data_points
        self.current_price_per_asset: dict[str, float] = {}

        self.__get_data_frames(assets)

    def __get_data_frames(self, assets: list[str]) -> None:
        """Get the data_frame for each asset

            Parameters:
                assets (list[str]): The list of assets to get the data_frame. Example: `["BTC", "ETH"]`

            Returns:
                None"""

        if not self.CRYPTOCOMPARE_API_KEY:
            raise ImportError('CRYPTOCOMPARE_API_KEY not found on .env')

        for asset in assets:
            complete_df_path = self.PATH_TO_COMPLETE_DATA_FRAME.format(
                asset)

            if os.path.exists(complete_df_path):
                print('> Fetching {} data_frame from cache'.format(asset))
                self.data_frames[asset] = pd.read_csv(complete_df_path)

            else:

                self.data_frames[asset] = self.__fetch_api(asset)

                self.data_frames[asset] = self.__add_indicators(asset)

                self.__save_complete_data_frame_to_csv(asset)

            self.train_data_frame[asset], self.test_data_frame[asset] = self.__split_data_frames(
                asset)

            self.df_features[asset] = self.__populate_df_features(
                asset, 'train')

    def __fetch_api(self, asset: str) -> pd.DataFrame:
        """Fetch the CryptoCompare API and return historical prices for a given asset

            Parameters:
                asset (str): The asset name. For a full asset list check: https://min-api.cryptocompare.com/documentation?key=Other&cat=allCoinsWithContentEndpoint

            Returns:
                raw_data_frame (pandas.Dataframe): The API 'Data' key response converted to a pandas Dataframe
        """

        print('> Fetching {} data_frame'.format(asset))

        headers = {'User-Agent': 'Mozilla/5.0',
                   'authorization': 'Apikey {}'.format(self.CRYPTOCOMPARE_API_KEY)}
        url = 'https://min-api.cryptocompare.com/data/histo{}?fsym={}&tsym={}&limit={}&e={}'.format(
            self.granularity, asset, self.currency, self.data_points, self.exchange)
        response = requests.get(url, headers=headers)
        json_response = response.json()
        status = json_response['Response']

        if status == "Error":
            print('Error fetching {} data_frame'.format(asset))
            raise AssertionError(json_response['Message'])

        result = json_response['Data']

        pandas_data_frame = pd.DataFrame(result)
        to_datetime_arg = pandas_data_frame['time']
        pandas_data_frame.drop(['time', 'conversionType',
                                'conversionSymbol'], axis=1, inplace=True)

        pandas_data_frame['Date'] = pd.to_datetime(
            arg=to_datetime_arg, utc=True, unit='s')

        return pandas_data_frame

    def __add_indicators(self, asset: str) -> pd.DataFrame:
        """Get the `self.raw_data_frame` data_frame and adds the market indicators for the given time series.

            Returns:
                raw_data_frame (pandas.DataFrame): A new data_frame based on `self.raw_data_frame` but with the indicators on it"""
        data_frame_with_indicators = {}
        data_frame_with_indicators[asset] = add_all_ta_features(
            self.data_frames[asset], open="open", high="high", low="low", close="close", volume="volumeto")
        return data_frame_with_indicators[asset]

    def __split_data_frames(self, asset: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split a data_frame for a selected asset into train_data_frame and test_data_frame

            Parameters:
                asset (str): asset name

            Returns:
                train_data_frame (ray.data.Dataset): A dataset containing the data to train
                test_data_frame (ray.data.Dataset): A dataset containing the data to test"""
        ray_data_frame = ray_data.from_pandas(self.data_frames[asset])
        train, test = ray_data_frame.train_test_split(test_size=0.25)
        return train.to_pandas(), test.to_pandas()

    def __save_complete_data_frame_to_csv(self, asset: str) -> None:
        """Save the data_frame with prices and indicators to a csv file to speed up future runnings

            Parameters:
                asset (str): The asset name

            Returns:
                None"""

        print('> Caching {} data_frame'.format(asset))

        path_to_data_frame = self.PATH_TO_COMPLETE_DATA_FRAME.format(
            asset)
        self.data_frames[asset].to_csv(path_to_data_frame)

    def __populate_df_features(self, asset: str, mode: str) -> None:
        if mode == 'train':
            return self.train_data_frame[asset].loc[:,
                                                    self.train_data_frame[asset].columns != 'Date']

        elif mode == 'test':
            return self.test_data_frame[asset].loc[:,
                                                   self.test_data_frame[asset].columns != 'Date']
