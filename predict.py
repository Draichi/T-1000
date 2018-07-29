from configs.functions import train_the_clf
from configs.vars import coin, requirement, dayss
from termcolor import cprint

class Predict:
    cprint('\n\n              {} changing {}% in {} days:\n\n'.format(coin, requirement*100, dayss), 'yellow')
    train_the_clf(coin)
