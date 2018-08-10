import sys
from termcolor import colored

if len(sys.argv) != 4:
	print(colored("Usage: python3 train.py [asset] [window] [episodes]", 'red'))
	exit()
import os
from agent import Agent
from functions import getState, getStockDataVec, sigmoid
from configs.vars import days, currency

asset_name = sys.argv[1]
window_size, episode_count = int(sys.argv[2]), int(sys.argv[3])

width = os.get_terminal_size().columns
asset = '{}_d{}_{}'.format(asset_name, days, currency)	

agent = Agent(window_size)
data = getStockDataVec(asset)
l = len(data) - 1
batch_size = 32

# prints formatted price
def formatPrice(n):
	if n < 0:
		return colored('Total profit: -BTC {0:.6f}'.format(abs(n)), 'red', attrs=['bold'])
	else:
		return colored('Total profit: BTC {0:.7f}'.format(abs(n)), 'green', attrs=['bold'])

print(chr(27) + "[2J")
print(colored('{}/{}'.format(asset_name.upper(), currency.upper()).center(width), 'blue',attrs=['bold']))
print(colored('{} {:.7f} ~> {} {:.7f}\n\n'.format(currency.upper(),data[0], currency.upper(), data[-1]).center(width), 'blue'))
print(colored('Trainning new model'.center(width), 'magenta',attrs=['bold']))
print(colored('Episode count: {}'.format(episode_count).center(width), 'magenta'))
print(colored('Window size: {}'.format(window_size).center(width), 'magenta'))
print(colored('Sample size: {}\n\n'.format(l).center(width), 'magenta'))

for e in range(episode_count+1):
    state = getState(data, 0, window_size + 1)
    total_profit = 0
    agent.inventory = []
    for t in range(l):
        action = agent.act(state)
        next_state = getState(data, t + 1, window_size + 1)
        reward = 0
        print("> {} BTC {:.7f}".format(t, data[t]), end='\r') #hold
        if action == 1: # buy
            agent.inventory.append(data[t])
            print(colored("> {} BTC {:.7f} |".format(t, data[t]), 'cyan'), end='\r')
        elif action == 2 and len(agent.inventory) > 0: # sell
            bought_price = agent.inventory.pop(0)
            reward = max(data[t] - bought_price, 0)
            total_profit += data[t] - bought_price
            print(colored("> {} BTC {:.7f} |".format(t, data[t]), 'yellow'), formatPrice(total_profit), end='\r')
        done = True if t == l - 1 else False
        agent.memory.append((state, action, reward, next_state, done))
        state = next_state
        if done:
            print('\n\n')
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print(colored("Episode {}/{}".format(str(e), str(episode_count)).center(width), 'cyan',  attrs=['bold']))
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print(formatPrice(total_profit).center(width))
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print('\n\n')
        if len(agent.memory) > batch_size:
            agent.expReplay(batch_size)
    if e % 10 == 0:
        agent.model.save("models/{}_d{}_e{}_w{}_c{}".format(asset_name,days, str(e), window_size, episode_count))
print(colored('D O N E'.center(width),'white','on_green',attrs=['bold']),'\n\n')