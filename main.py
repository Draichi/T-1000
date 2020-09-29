if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(description='T-1000 bot')
	parser.add_argument('-a', action="store", dest='assets', nargs='+', help='assets to test')
	parser.add_argument('-c', action="store", dest="currency", type=str, default='DAI')
	parser.add_argument('-g', action="store", dest="granularity", type=str, default='hour')
	parser.add_argument('-d', action="store", dest="datapoints", type=int, default=150)
	parser.add_argument('-t', action="store", dest="timesteps", default=3e6)
	parser.add_argument('-f', action="store", dest="checkpoint_freq", type=int, default=100)
	parser.add_argument('-b', action="store", dest="initial_account_balance", type=int, default=300)
	parser.add_argument('-e', action="store", dest="exchange", type=str, default='Binance')
	parser.add_argument('-ex', action="store", dest="exchange_commission", type=int, default=0.00075)
	parser.add_argument('-lr', action="store", dest="lr_schedule", default=[[[0, 1e-4], [1e6, 8e-5]]])
	parser.add_argument('--algo', action="store", dest="algo", default='PPO', type=str)
	parser.add_argument('--checkpoint-path', action="store", dest="checkpoint_path", type=str)
	parser.add_argument('--version', action='version', version='1.0')
	args = parser.parse_args()

	if not args.checkpoint_path and not args.assets:
		raise ValueError('-a cannot be null')
	from utils import loading
	loading()
	from t_1000.application import T1000

	env = T1000(assets=args.assets,
				currency=args.currency,
				granularity=args.granularity,
				datapoints=args.datapoints,
				checkpoint_path=args.checkpoint_path,
				initial_account_balance=args.initial_account_balance,
				exchange_commission=args.exchange_commission,
				exchange=args.exchange)

	if not args.checkpoint_path: # train
		env.train(timesteps=int(float(args.timesteps)),
		          checkpoint_freq=args.checkpoint_freq,
		          lr_schedule=args.lr_schedule,
		          algo=args.algo)
	else: # test
		env.backtest(checkpoint_path=args.checkpoint_path)

              
