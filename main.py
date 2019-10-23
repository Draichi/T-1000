if __name__ == '__main__':
    from utils import random_emojis
    random_emojis()
    from core_main import Nostradamus
    env = Nostradamus(assets=['OMG','BTC','ETH'],
                      currency='USDT',
                      granularity='day',
                      datapoints=600)

    # env.train(timesteps=5e4,
    #           checkpoint_freq=10,
    #           lr_schedule=[
    #               [
    #                   [0, 7e-5],  # [timestep, lr]
    #                   [5e4, 7e-6],
    #               ],
    #               [
    #                   [0, 6e-5],
    #                   [5e4, 6e-6],
    #               ]
    #           ],
    #           algo='PPO')
    env.backtest(checkpoint_path='results/t-100_test/1_2019-10-22_23-26-05tgaq0nft/checkpoint_10/checkpoint-10')
