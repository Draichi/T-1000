if __name__ == '__main__':
    import emoji
    import random
    from termcolor import colored
    emojis = [':fire:', ':moneybag:', ':yen:', ':dollar:', ':pound:', ':floppy_disk:', ':euro:', ':credit_card:', ':money_with_wings:', ':large_blue_diamond:', ':gem:', ':bar_chart:', ':crystal_ball:', ':chart_with_downwards_trend:', ':chart_with_upwards_trend:', ':large_orange_diamond:']


    print(colored('> ' + emoji.emojize(random.choice(emojis) + ' loading...', use_aliases=True), 'green'))
    # print(emoji.emojize(':fire: :moneybag: :yen: :dollar: :pound: :floppy_disk: :euro: :credit_card: :money_with_wings:', use_aliases=True))
    import yes_man
    env = yes_man.Trade(assets=['OMG','BTC','ETH'],
                        currency='USDT',
                        granularity='hour',
                        datapoints=100)

    # env.train(timesteps=3e10,
    #           checkpoint_freq=30,
    #           lr_schedule=[
    #               [
    #                   [0, 7e-5],  # [timestep, lr]
    #                   [100, 7e-6],
    #               ],
    #               [
    #                   [0, 6e-5],
    #                   [100, 6e-6],
    #               ]
    #           ],
    #           algo='PPO')
    env.backtest(checkpoint_file='/home/lucas/ray_results/vai/PPO_YesMan-v1_1_lr_schedule=[[0, 6e-05], [100, 6e-06]]_2019-08-10_13-14-42nsy2n_63')
