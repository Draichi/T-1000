import numpy as np
import math, os, keras
from termcolor import colored
from keras.models import load_model
from configs.agent import Agent
from configs.vars import days, currency, todays_day, todays_month, terminal_width, batch_size, wallet, fees, n_orders
#------------------------------------------------------------->
def div():
	print(colored("-"*terminal_width,'white'))
#------------------------------------------------------------->
# prints formatted price
def format_price(n):
	if n <= wallet:
		return colored('{} {:.7f}'.format(currency.upper(), abs(n)), 'yellow', attrs=['bold'])
	else:
		return colored('{} {:.7f}'.format(currency.upper(), abs(n)), 'cyan', attrs=['bold'])
#------------------------------------------------------------->
# returns the vector containing stock data from a fixed file
def get_stock_data_vec(key):
	vec = []
	lines = open("datasets/" + key + ".csv", "r").read().splitlines()
	for line in lines[1:]:
		# ------1=price, 2=market_cap, 3=vol------
		vec.append([float(line.split(",")[1]), float(line.split(",")[2]), float(line.split(",")[3])])
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
	res = []
	for i in range(n - 1):
		res.append([ _sigmoid(block[i+1][0] - block[i][0]) , _sigmoid(block[i+1][1] - block[i][1]), _sigmoid(block[i+1][2] - block[i][2]) ])
	return np.array([res])
#------------------------------------------------------------->
def operate(agent, asset_name, window_size, model_name=False):
	asset = '{}-{}_{}_d{}_{}'.format(todays_day, todays_month, asset_name, days, currency)	
	data = get_stock_data_vec(asset)
	market_first = data[0][0]
	market_last = data[-1][0]
	market_percentage = ((market_last - market_first) / ((market_last + market_first) / 2))*100
	l = len(data) - 1
	state = get_state(data, 0, window_size + 1)
	w = wallet
	agent.inventory = []
	place_order = 0
	#------------------------------------------------------------->
	for t in range(l):
		reward = 0
		reward_counter = 0
		next_state = get_state(data, t + 1, window_size + 1)
		price = data[t][0]
		total_price_plus_fee = (price*n_orders) + fees
		total_price_minus_fee = (price*n_orders) - fees
		# --------force buy at first? testig---------
		if t == 0 and model_name == False:
			action = 1 #buy if its the beginning
		else:
			action = agent.act(state)
		# action = agent.act(state)
		# --------force buy at first? testig---------
		print("> {} {} {:.7f}".format(t, currency.upper(),price), end='\r')
		# --------buy--------
		if action == 1:
			if w >= total_price_plus_fee:
				w -= total_price_plus_fee
				place_order += 1
				agent.inventory.append(total_price_plus_fee)
				print(colored("> {} {} {:.7f} | Wallet:".format(t, currency.upper(), price), 'green'), format_price(w))
		# ---------sell-------
		elif action == 2 and len(agent.inventory) > 0:
			place_order += 1
			bought_price = agent.inventory.pop(0)
			profit = total_price_minus_fee - bought_price
			w += total_price_minus_fee
			reward = max(profit, 0)
			print(colored("> {} {} {:.7f} | Wallet:".format(
				t, currency.upper(), price), 'red'), format_price(w), "| Profit: {} {}".format(currency.upper(), profit))
		# ----------sell all at end---------
		elif (t == l - 2) and len(agent.inventory) > 0:
			n_assets = len(agent.inventory)
			place_order += n_assets
			for _ in range(n_assets):
				bought_price = agent.inventory.pop(0)
				profit = price - fees - bought_price
				w += profit
				reward = max(profit, 0)
		done = True if t == l - 1 else False
		# ---------add all or half? testing----------
		if reward == 0:
			reward_counter += 1
		if reward > 0 or reward_counter < (batch_size*.66):
			agent.memory.append((state, action, reward, next_state, done))
		# agent.memory.append((state, action, reward, next_state, done))
		# ---------add all or half? testing----------
		state = next_state
		if len(agent.memory) > batch_size:
			agent.expReplay(batch_size)
	#------------------------------------------------------------->
	wallet_percentage = ((w - wallet) / ((w + wallet) / 2))*100	
	# -----save the model if profit is made ----
	if w > wallet:
		agent.model.save("models/{}-{}_{}_d{}_w{}_{}_{:.0f}->{:.0f}_b{}".format(
			todays_day,todays_month,asset_name,days,window_size,currency,wallet,w,batch_size))
	#------------------------------------------------------------->
	div()
	print(colored('|              PRICE              |      SAMPLE      | WINDOW |'.center(terminal_width), 'white', attrs=['bold']))
	print(colored('| {} {:<8.5f}  ==>  {} {:8.5f} | {:<4} = {:^4} days | {:^6} |'.format(
		currency.upper(),market_first, currency.upper(), market_last, (l-1), days, window_size).center(terminal_width), 'white', attrs=['bold']))
	div()
	#------------------------------------------------------------->
	print(colored('|   MARKET % |  WALLET %  | ACTIONS | ORDERS/ACTION |    WALLET    |'.center(terminal_width), 'white', attrs=['bold']))
	print(colored('| {:8.2f} % | {:8.2f} % | {:^7} | {:^14}| {} {:8} |'.format(
		market_percentage, wallet_percentage, place_order, n_orders,currency.upper(),wallet).center(terminal_width), 'white', attrs=['bold']))
	div()
	#------------------------------------------------------------->
	print('          Final Wallet: {}'.format(format_price(w)).center(terminal_width))
	div()
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