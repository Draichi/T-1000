import numpy as np
import math, os
from termcolor import colored
from configs.vars import currency
width = os.get_terminal_size().columns

# prints formatted price
def formatPrice(n):
	if n < 0:
		return colored('Total profit: -{} {:.6f}'.format(currency.upper(), abs(n)).center(width), 'red', attrs=['bold'])
	else:
		return colored('Total profit: {} {:.7f}'.format(currency.upper(), abs(n)).center(width), 'green', attrs=['bold'])
	# return ("-BTC " if n < 0 else "BTC ") + "{0:.7f}".format(abs(n))

# returns the vector containing stock data from a fixed file
def getStockDataVec(key):
	vec = []
	lines = open("datasets/" + key + ".csv", "r").read().splitlines()
	for line in lines[1:]:
		vec.append(float(line.split(",")[2]))# 1=marketcap, 2=prices, 3=vol
	return vec

# returns the sigmoid
def sigmoid(x):
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

# returns an an n-day state representation ending at time t
def getState(data, t, n):
	d = t - n + 1
	block = data[d:t + 1] if d >= 0 else -d * [data[0]] + data[0:t + 1] # pad with t0
	res = []
	for i in range(n - 1):
		res.append(sigmoid(block[i + 1] - block[i]))
	return np.array([res])

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
	""", 'green'))
