if __name__ == '__main__':
    import yes_man
    env = yes_man.Env(assets=['OMG,BTC,ETH'],
                      currency='USDT',
                      granularity='hour',
                      datapoints=1000,
                      algo='PPO')
    env.train(timesteps=3e10,
              checkpoint_freq=30,
              lr_schedule=[
                    [
                        [0, 7e-5], # [timestep, lr]
                        [TIMESTEPS_TOTAL, 7e-6],
                    ],
                    [
                        [0, 6e-5],
                        [TIMESTEPS_TOTAL, 6e-6],
                    ]
              ])
    env.rollout()