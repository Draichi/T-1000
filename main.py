if __name__ == '__main__':
    print('> loading...')
    import yes_man
    env = yes_man.Trade(assets=['OMG','BTC','ETH'],
                        currency='USDT',
                        granularity='hour',
                        datapoints=100)

    env.train(timesteps=3e10,
              checkpoint_freq=30,
              lr_schedule=[
                  [
                      [0, 7e-5],  # [timestep, lr]
                      [100, 7e-6],
                  ],
                  [
                      [0, 6e-5],
                      [100, 6e-6],
                  ]
              ],
              algo='PPO')
    # env.backtest(checkpoint_file='../../file')
