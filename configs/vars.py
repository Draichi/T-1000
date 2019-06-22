############ TRAIN VARIABLES ################
SYMBOL_1, SYMBOL_2, SYMBOL_3 = 'LTC', 'ETH', 'OMG'
TRADE_INSTRUMENT = 'USDT'
LIMIT = 1500 # how many datapoints (max 2000)
HISTO = 'minute'
TIMESTEPS_TOTAL = 3.5e6 #1e6 = 1M
CHECKPOINT_FREQUENCY = 50
LEARNING_RATE_SCHEDULE = [
    [
        [0, 7e-5], # [timestep, lr]
        [TIMESTEPS_TOTAL, 7e-6],
    ],
    [
        [0, 6e-5],
        [TIMESTEPS_TOTAL, 6e-6],
    ]
]
RESTORE_PATH = None #  path to checkpoint file to continue trainning
INITIAL_ACCOUNT_BALANCE = 10000
COMMISSION = 0.00075 # BitMEX

############ FUNCTIONS VARIABLES ################
DF_TRAIN_SIZE = 0.75

############ RENDER VARIABLES ################
VOLUME_CHART_HEIGHT = 0.33
LOOKBACK_WINDOW_SIZE = 40
CANDLESTICK_WIDTH = {
    "day": 1,
    "hour": 0.4,
    "minute": 0.0006
}
BALANCE_COLOR = ['#ffa929', '#ff297f', '#7fff29', '#297fff']
UP_COLOR = '#00b909'
DOWN_COLOR = '#c60606'
UP_TEXT_COLOR = '#00b909'
DOWN_TEXT_COLOR = '#c60606'
BUY_N_HOLD_COLOR = '#297fff'
BOT_COLOR = '#ffaa00'
