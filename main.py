import argparse

parser = argparse.ArgumentParser(description='Short sample app')

parser.add_argument('-a', action="store", dest='assets', nargs='+', help='assets to test')
parser.add_argument('-c', action="store", dest="currency", type=str, default='BTC')
parser.add_argument('-g', action="store", dest="granularity", type=str, default='hour')
parser.add_argument('-d', action="store", dest="datapoints", type=int, default=150)
parser.add_argument('-t', action="store", dest="timesteps", type=int, default=3e6)
parser.add_argument('-f', action="store", dest="checkpoint_freq", type=int, default=10)
parser.add_argument('-lr', action="store", dest="lr_schedule", default=[[[0, 7e-5], [1e6, 6e-5], [3e6, 5e-5]]])
parser.add_argument('--algo', action="store", dest="algo", default='PPO', type=str)
parser.add_argument('--checkpoint-path', action="store", dest="checkpoint_path", type=str)
parser.add_argument('--version', action='version', version='1.0')

result = parser.parse_args()
print(type(result.checkpoint_path))
print(result.checkpoint_path)
print(type(result.assets)) # None
print(result.assets)
quit()
if __name__ == '__main__':
  # if not result.assets
    from utils.data_processing import loading
    loading()
    from t_1000.application.core import Nostradamus
    env = Nostradamus(assets=['XRP','BCH','LTC','BNB'],
                      currency='BTC',
                      granularity='day',
                      datapoints=300)

    env.train(timesteps=3e5,
              checkpoint_freq=10,
              lr_schedule=[
                  [
                      [0, 7e-5],  # [timestep, lr]
                      [1e6, 7e-6],
                  ],
                #   [
                #       [0, 6e-5],
                #       [1e6, 6e-6],
                #   ],
                #   [
                #       [0, 5e-5],
                #       [1e6, 5e-6],
                #   ]
              ],
              algo='PPO')
              
    # checkpoint_path = 'results/t-1000/1_2020-09-03_07-41-091y8hnjtt/checkpoint_10/checkpoint-10'
    # env.backtest(checkpoint_path=checkpoint_path)
