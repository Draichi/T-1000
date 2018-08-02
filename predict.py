from configs.functions import train_the_clf
from configs.vars import coin, requirement, forecast_days
from termcolor import cprint

class Predict:
    text = '\n\n              {} changing {}% in {} days:\n\n'.format(coin, requirement*100, forecast_days)
    cprint(text.upper(), 'yellow')
    train_the_clf(coin)
