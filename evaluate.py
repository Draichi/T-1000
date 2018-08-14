import sys
from termcolor import colored
if len(sys.argv) != 3:
	print(colored("Usage: python evaluate.py [asset] [model]", 'red', attrs=['bold']))
	exit()
import keras, os
from keras.models import load_model
from configs.agent import Agent
from configs.functions import *
from configs.vars import days, currency, todays_day, todays_month, terminal_width, batch_size
#------------------------------------------------------------->
asset_name, model_name = sys.argv[1], sys.argv[2]
#------------------------------------------------------------->
agent = Agent(window_size, True, model_name)
operate(agent, asset_name, model_name)
print(colored('D O N E'.center(terminal_width),'white','on_green',attrs=['bold']))