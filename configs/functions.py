import numpy as np
import math, os, keras
from termcolor import colored
from keras.models import load_model
from configs.agent import Agent
from configs.vars import days, currency, todays_day, todays_month, terminal_width, batch_size, wallet, fees, n_orders
#------------------------------------------------------------->
width = os.get_terminal_size().columns
#------------------------------------------------------------->
def _div():
	print(colored("-"*terminal_width,'white'))

# prints formatted price
def format_price(n):
	if n <= wallet:
		return colored('Wallet: {:3} {:.7f}'.format(currency.upper(), abs(n)), 'yellow', attrs=['bold'])
	else:
		return colored('Wallet: {:4} {:.7f}'.format(currency.upper(), abs(n)), 'cyan', attrs=['bold'])
#------------------------------------------------------------->
# returns the vector containing stock data from a fixed file
def get_stock_data_vec(key):
	vec = []
	lines = open("datasets/" + key + ".csv", "r").read().splitlines()
	for line in lines[1:]:
		vec.append([float(line.split(",")[1]), float(line.split(",")[2]), float(line.split(",")[3])])# 1=price, 2=market_cap, 3=vol
	# print('-- debug:',vec)
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
	# mudar aqui
	d = t - n + 1
	block = data[d:t + 1] if d >= 0 else -d * [data[0]] + data[0:t + 1] # pad with t0
	
	# entender e adaptar o block
	res = []
	for i in range(n - 1):
		# dar o append de um sigmoid ou 2?
		res.append([ _sigmoid(block[i+1][0] - block[i][0]) , _sigmoid(block[i+1][1] - block[i][1]), _sigmoid(block[i+1][2] - block[i][2]) ])
	# print('======= debug:',np.array([res]))
	# print(res)
	# quit()
	return np.array([res])
#------------------------------------------------------------->
def operate(agent, asset_name, window_size, model_name=False):
	asset = '{}-{}_{}_d{}_{}'.format(todays_day, todays_month, asset_name, days, currency)	
	data = get_stock_data_vec(asset)
	l = len(data) - 1
	half_length = l/2
	state = get_state(data, 0, window_size + 1)
	# total_profit = 0
	w = wallet
	agent.inventory = []
	place_order = 0
	#------------------------------------------------------------->
	for t in range(l):
		reward = 0
		reward_counter = 0
		next_state = get_state(data, t + 1, window_size + 1)
		price = data[t][0]
		total_price = (price*n_orders) + fees
		if t == 0:
			action = 1 #buy if its the beginning
		else:
			action = agent.act(state)
		print("> {} {} {:.7f}".format(t, currency.upper(),price), end='\r') #hold
		if action == 1: # buy
			# print('data ---- ',price)
			# print('wallet ---- ',w)
			if w >= total_price:
				w -= total_price # implemetn fees
				place_order += 1
				agent.inventory.append(total_price)
				if not model_name == False:
					print(colored("> {} {} {:.7f} |".format(t, currency.upper(), price), 'green'), format_price(w))
				else:			
					print(colored("> {} {} {:.7f} |".format(t, currency.upper(), price), 'green'), format_price(w), end='\r')
		elif action == 2 and len(agent.inventory) > 0: # sell
			place_order += 1
			bought_price = agent.inventory.pop(0)
			profit = price*n_orders - fees - bought_price
			w += profit
			# wallet_diff = w - wallet
			# reward = w
			reward = max(profit, 0) # balancing the reward
			if not model_name == False:
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), price), 'red'), format_price(w), " - Reward: {}".format(reward))
			else:
				print(colored("> {} {} {:.7f} |".format(t, currency.upper(), price), 'red'), format_price(w), " - Reward: {}".format(reward), end='\r')
		# elif (t == l - 2) and len(agent.inventory) > 0: # end
		# 	n_assets = len(agent.inventory)
		# 	place_order += n_assets
		# 	for _ in range(n_assets):
		# 		bought_price = agent.inventory.pop(0)
		# 		profit = price - fees - bought_price
		# 		w += profit
		# 		reward = max(profit, 0) # no balancing the reward
		done = True if t == l - 1 else False
		if reward == 0:
			reward_counter += 1
		if reward > 0 or reward_counter < half_length: # do not append if we alredy appended half of lenght with reward 0.
			agent.memory.append((state, action, reward, next_state, done))
		state = next_state
		if done:
			_div()
			print('        {}'.format(format_price(w).center(terminal_width)))
			print('Actions: {}'.format(place_order).center(terminal_width))
			_div()
		if len(agent.memory) > batch_size:
			agent.expReplay(batch_size)
	#------------------------------------------------------------->
	print(colored('{}/{}'.format(asset_name.upper(), currency.upper()).center(terminal_width), 'white', attrs=['bold']))
	if not model_name == False:
		print(colored('MODEL: {}'.format(model_name).center(terminal_width), 'white', attrs=['bold']))
	_div()
	print(colored('            PRICE                                   SAMPLE                                WINDOW              '.center(terminal_width), 'magenta'))
	print(colored('{} {:.7f}  ==>  {} {:.7f}  {:12} ==> {:4} days  {:1}'.format(currency.upper(),data[0][0], currency.upper(), data[-1][0], (l-1), days, window_size).center(terminal_width), 'magenta', attrs=['bold']))
	# print(colored('PRICE  {} {:.7f}  ==>  {} {:.7f}'.format(currency.upper(),data[0][0], currency.upper(), data[-1][0]).center(terminal_width), 'magenta', attrs=['bold']))
	# print(colored('SAMPLE  {:12}  ==> {:9} days'.format((l-1), days).center(terminal_width), 'magenta', attrs=['bold']))
	# print(colored('WINDOW                ==> {:14}'.format(window_size).center(terminal_width), 'magenta', attrs=['bold']))
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