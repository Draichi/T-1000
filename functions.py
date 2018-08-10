import numpy as np
import math, os
from termcolor import colored
width = os.get_terminal_size().columns

# prints formatted price
def formatPrice(n):
	if n < 0:
		return colored('Total profit: -BTC {0:.6f}'.format(abs(n)).center(width), 'red', attrs=['bold'])
	else:
		return colored('Total profit: BTC {0:.7f}'.format(abs(n)).center(width), 'green', attrs=['bold'])
	# return ("-BTC " if n < 0 else "BTC ") + "{0:.7f}".format(abs(n))

# returns the vector containing stock data from a fixed file
def getStockDataVec(key):
	vec = []
	lines = open("datasets/" + key + ".csv", "r").read().splitlines()

	for line in lines[1:]:
		vec.append(float(line.split(",")[1]))

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
