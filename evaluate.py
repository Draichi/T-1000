import sys
from termcolor import colored

if len(sys.argv) != 3:
	print(colored("Usage: python evaluate.py [asset] [model]", 'red', attrs=['bold']))
	exit()
import keras, os
from keras.models import load_model
from agent import Agent
from functions import *
from configs.vars import days, currency, todays_day, todays_month

width = os.get_terminal_size().columns
asset_name, model_name = sys.argv[1], sys.argv[2]
model = load_model("models/" + model_name)
window_size = model.layers[0].input.shape.as_list()[1]
asset = '{}-{}_{}_d{}_{}'.format(todays_day, todays_month, asset_name, days, currency)	

agent = Agent(window_size, True, model_name)
data = getStockDataVec(asset)
l = len(data) - 1
batch_size = 32
state = getState(data, 0, window_size + 1)
total_profit = 0
agent.inventory = []

print(chr(27) + "[2J")
print(colored('{}/{}'.format(asset_name.upper(), currency.upper()).center(width), 'cyan', attrs=['reverse','bold']))
print(colored('{} {:.7f} ~> {} {:.7f}'.format(currency.upper(),data[0], currency.upper(), data[-1]).center(width), 'cyan', attrs=['bold']))
print(colored('Model: {} - Window size: {}'.format(model_name, window_size).center(width), 'cyan', attrs=['bold']))
print(colored('Sample size: {} - {} days'.format(l, days).center(width), 'cyan', attrs=['underline','bold']))

for t in range(l):
	action = agent.act(state)
	next_state = getState(data, t + 1, window_size + 1)
	reward = 0
	print("> {} {} {:.7f}".format(t, currency.upper(),data[t]), end='\r') #hold
	if action == 1: # buy
		agent.inventory.append(data[t])
		print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'cyan'), formatPrice(total_profit), end='\r')
	elif action == 2 and len(agent.inventory) > 0: # sell
		bought_price = agent.inventory.pop(0)
		reward = max(data[t] - bought_price, 0)
		total_profit += data[t] - bought_price
		print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'yellow'), formatPrice(total_profit), end='\r')
	done = True if t == l - 1 else False
	agent.memory.append((state, action, reward, next_state, done))
	state = next_state
	if done:
		print(colored("-----------------------------".center(width), 'cyan'))
		print(formatPrice(total_profit).center(width))
		print(colored("-----------------------------".center(width),'cyan'))
	if len(agent.memory) > batch_size:
		agent.expReplay(batch_size)
print(colored('D O N E'.center(width),'white','on_green',attrs=['bold']))