from sklearn import svm, model_selection, neighbors
from config.functions import *
from config.vars import *
from datetime import date
from setup import *


if __name__ == '__main__':
    if datetime.now() == 5:
        from setup import *
    cprint(
        '\n\n              {} changing {}% in {} days:\n\n'.format(
            COIN, 
            REQUIREMENT*100, 
            HOW_MANY_DAYS
        ),
        'yellow'
    )
    train_the_clf(COIN)
