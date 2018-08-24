import sys
from termcolor import colored
if len(sys.argv) != 3:
	print(colored("Usage: python3 evaluate.py [asset] [model]", 'red', attrs=['bold']))
	exit()
import keras, os
from keras.models import load_model
from configs.agent import Agent
from configs.functions import *
from configs.vars import days, currency, todays_day, todays_month, terminal_width, batch_size
#------------------------------------------------------------->
asset_name, model_name = sys.argv[1], sys.argv[2]
model = load_model("models/" + model_name)
window_size = model.layers[0].input.shape.as_list()[1]
#------------------------------------------------------------->
print(chr(27) + "[2J")
#------------------------------------------------------------->
agent = Agent(window_size, True, model_name)
operate(
	agent=agent,
	asset_name=asset_name,
	window_size=window_size,
	model_name=model_name
)
print(colored('D O N E'.center(terminal_width),'white','on_green',attrs=['bold']))