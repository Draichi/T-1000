import numpy as np
import math, os, keras
from termcolor import colored
from keras.models import load_model
from configs.agent import Agent
from configs.vars import days, currency, todays_day, todays_month, terminal_width, batch_size
#------------------------------------------------------------->
width = os.get_terminal_size().columns
#------------------------------------------------------------->
def _div():
	print(colored("-"*terminal_width,'white'))

# prints formatted price
def format_price(n):
	if n < 0:
		return colored('Total profit: -{:3} {:.7f}'.format(currency.upper(), abs(n)), 'yellow', attrs=['bold'])
	else:
		return colored('Total profit: {:4} {:.7f}'.format(currency.upper(), abs(n)), 'cyan', attrs=['bold'])
#------------------------------------------------------------->
# returns the vector containing stock data from a fixed file
def get_stock_data_vec(key):
	vec = []
	lines = open("datasets/" + key + ".csv", "r").read().splitlines()
	for line in lines[1:]:
		vec.append(float(line.split(",")[2]))# 1=marketcap, 2=prices, 3=vol
	return vec
#------------------------------------------------------------->
# returns the sigmoid
def _sigmoid(x):
	try:
		if x < 0:
			return 1 - 1 / (1 + math.exp(x))
		return 1 / (1 + math.exp(-x))
	except OverflowError as err:
		print("Overflow err: {0} - Val of x: {1}".format(err, x))
	except ZeroDivisionError:
		print("division by zero!")
	except Exception as err:
		print("Error in sigmoid: " + err)
#------------------------------------------------------------->
# returns an an n-day state representation ending at time t
def get_state(data, t, n):
	d = t - n + 1
	block = data[d:t + 1] if d >= 0 else -d * [data[0]] + data[0:t + 1] # pad with t0
	res = []
	for i in range(n - 1):
		res.append(_sigmoid(block[i + 1] - block[i]))
	return np.array([res])
#------------------------------------------------------------->
def operate(agent, asset_name, window_size, model_name=False):
	asset = '{}-{}_{}_d{}_{}'.format(todays_day, todays_month, asset_name, days, currency)	
	data = get_stock_data_vec(asset)
	l = len(data) - 1
	state = get_state(data, 0, window_size + 1)
	total_profit = 0
	agent.inventory = []
	#------------------------------------------------------------->
	
	for t in range(l):
		action = agent.act(state)
		next_state = get_state(data, t + 1, window_size + 1)
		reward = 0
		print("> {} {} {:.7f}".format(t, currency.upper(),data[t]), end='\r') #hold
		if action == 1: # buy
			agent.inventory.append(data[t])
			if not model_name == False:
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'green'), format_price(total_profit))
			else:			
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'green'), format_price(total_profit), end='\r')
		elif action == 2 and len(agent.inventory) > 0: # sell
			bought_price = agent.inventory.pop(0)
			reward = max(data[t] - bought_price, 0)
			total_profit += data[t] - bought_price
			if not model_name == False:
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'red'), format_price(total_profit))
			else:
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), data[t]), 'red'), format_price(total_profit), end='\r')
		done = True if t == l - 1 else False
		agent.memory.append((state, action, reward, next_state, done))
		state = next_state
		if done:
			_div()
			print('        {}'.format(format_price(total_profit).center(terminal_width)))
			_div()
		if len(agent.memory) > batch_size:
			agent.expReplay(batch_size)
	#------------------------------------------------------------->
	print(colored('{}/{}'.format(asset_name.upper(), currency.upper()).center(terminal_width), 'white', attrs=['bold']))
	if not model_name == False:
		print(colored('MODEL: {}'.format(model_name).center(terminal_width), 'white', attrs=['bold']))
	_div()
	print(colored('PRICE  {} {:.7f}  ==>  {} {:.7f}'.format(currency.upper(),data[0], currency.upper(), data[-1]).center(terminal_width), 'magenta', attrs=['bold']))
	print(colored('SAMPLE  {:12}  ==> {:9} days'.format((l-1), days).center(terminal_width), 'magenta', attrs=['bold']))
	print(colored('WINDOW                ==> {:14}'.format(window_size).center(terminal_width), 'magenta', attrs=['bold']))
	_div()
	#------------------------------------------------------------->

#------------------------------------------------------------->
def print_dollar():
	print(chr(27) + "[2J")
	print(colored("""
   ||====================================================================||
   ||//$\\\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\//$\\\||
   ||(100)==================| FEDERAL RESERVE NOTE |================(100)||
   ||\\\$//        ~         '------========--------'                \\\$//||
   ||<< /        /$\              // ____ \\\                         \ >>||
   ||>>|  12    //L\\\            // ///..) \\\         L38036133B   12 |<<||
   ||<<|        \\\ //           || <||  >\  ||                        |>>||
   ||>>|         \$/            ||  $$ --/  ||        One Hundred     |<<||
||====================================================================||>||
||//$\\\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\//$\\\||<||
||(100)==================| FEDERAL RESERVE NOTE |================(100)||>||
||\\\$//        ~         '------========--------'                \\\$//||\||
||<< /        /$\              // ____ \\\                         \ >>||)||
||>>|  12    //L\\\            // ///..) \\\         L38036133B   12 |<<||/||
||<<|        \\\ //           || <||  >\  ||                        |>>||=||
||>>|         \$/            ||  $$ --/  ||        One Hundred     |<<||
||<<|      L38036133B        *\\\  |\_/  //* series                 |>>||
||>>|  12                     *\\\/___\_//*   1989                  |<<||
||<<\      Treasurer     ______/Franklin\________     Secretary 12 />>||
||//$\                 ~|UNITED STATES OF AMERICA|~               /$\\\||
||(100)===================  ONE HUNDRED DOLLARS =================(100)||
||\\\$//\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\\\$//||
||====================================================================||           
	""", 'green', attrs=['bold']))