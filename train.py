import sys
from termcolor import colored

if len(sys.argv) != 4:
	print(colored("Usage: python3 train.py [asset] [window] [episodes]", 'red'))
	exit()
import os
from agent import Agent
from functions import getState, getStockDataVec, sigmoid
from configs.vars import days, currency, todays_day, todays_month

asset_name = sys.argv[1]
window_size, episode_count = int(sys.argv[2]), int(sys.argv[3])

width = os.get_terminal_size().columns
asset = '{}-{}_{}_d{}_{}'.format(todays_day, todays_month, asset_name, days, currency)	

agent = Agent(window_size)
data = getStockDataVec(asset)
l = len(data) - 1
batch_size = 32

# prints formatted price
def formatPrice(n):
	if n < 0:
		return colored('Total profit: -{} {:.6f}'.format(currency.upper(), abs(n)), 'red', attrs=['bold'])
	else:
		return colored('Total profit: {} {:.7f}'.format(currency.upper(), abs(n)), 'green', attrs=['bold'])

print(chr(27) + "[2J")
print(colored('{}/{}'.format(asset_name.upper(), currency.upper()).center(width), 'blue',attrs=['bold']))
print(colored('{} {:.7f} ~> {} {:.7f}'.format(currency.upper(),data[0], currency.upper(), data[-1]).center(width), 'blue'))
print(colored('{} days'.format(days).center(width), 'blue',attrs=['bold']))
print(colored('Episode count: {}'.format(episode_count).center(width), 'blue'))
print(colored('Window size: {}'.format(window_size).center(width), 'blue'))
print(colored('Sample size: {}'.format(l).center(width), 'blue'))

for e in range(episode_count+1):
    state = getState(data, 0, window_size + 1)
    total_profit = 0
    agent.inventory = []
    for t in range(l):
        action = agent.act(state)
        next_state = getState(data, t + 1, window_size + 1)
        reward = 0
        print("> {} {} {:.7f}".format(t, currency.upper(), data[t]), end='\r') #hold
        if action == 1: # buy
            agent.inventory.append(data[t])
            print(colored("> {} {} {:.7f} |".format(t, currency.upper(),data[t]), 'cyan'), end='\r')
        elif action == 2 and len(agent.inventory) > 0: # sell
            bought_price = agent.inventory.pop(0)
            reward = max(data[t] - bought_price, 0)
            total_profit += data[t] - bought_price
            print(colored("> {} {} {:.7f} |".format(t, currency.upper(),data[t]), 'yellow'), formatPrice(total_profit), end='\r')
        done = True if t == l - 1 else False
        agent.memory.append((state, action, reward, next_state, done))
        state = next_state
        if done:
            print('\n\n')
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print(colored("Episode {}/{} - Window size {}".format(str(e), str(episode_count), window_size).center(width), 'cyan',  attrs=['bold']))
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print(formatPrice(total_profit).center(width))
            print(colored("---------------------------------------------".center(width), 'cyan'))
            print('\n\n')
        if len(agent.memory) > batch_size:
            agent.expReplay(batch_size)
    if e % 10 == 0:
        agent.model.save("models/{}-{}_{}_d{}_e{}_w{}_c{}_{}".format(todays_day, todays_month, asset_name,days, str(e), window_size, episode_count, currency))
print(colored('D O N E'.center(width),'white','on_green',attrs=['bold']),'\n\n')