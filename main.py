if __name__ == '__main__':
    from utils import loading
    loading()
    from core_main import Nostradamus
    env = Nostradamus(assets=['XRP','BCH','LTC','BNB'],
                      currency='BTC',
                      granularity='day',
                      datapoints=600)

    env.train(timesteps=1e6,
              checkpoint_freq=50,
              lr_schedule=[
                  [
                      [0, 7e-5],  # [timestep, lr]
                      [1e6, 7e-6],
                  ],
                  [
                      [0, 6e-5],
                      [1e6, 6e-6],
                  ],
                  [
                      [0, 5e-5],
                      [1e6, 5e-6],
                  ]
              ],
              algo='PPO')
              
    # checkpoint_path = 'results/t-100_test/1_2019-10-28_16-53-531fzmn26h/checkpoint_250/checkpoint-250'
    # env.backtest(checkpoint_path=checkpoint_path)
