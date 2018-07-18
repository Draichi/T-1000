from config.functions import train_the_clf
from config.vars import coin, requirement, days
from termcolor import cprint

class Predict:
    cprint('\n\n              {} changing {}% in {} days:\n\n'.format(coin, requirement*100, days), 'yellow')
    train_the_clf(coin)
