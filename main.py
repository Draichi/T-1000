if __name__ == '__main__':
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
