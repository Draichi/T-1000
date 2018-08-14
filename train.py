import sys
from termcolor import colored
if len(sys.argv) != 4:
	print(colored("Usage: python3 train.py [asset] [window] [episodes]", 'red'))
	exit()
import os
from configs.agent import Agent
from configs.functions import *
from configs.vars import days, currency, todays_day, todays_month, batch_size
#------------------------------------------------------------->
asset_name = sys.argv[1]
window_size, episode_count = int(sys.argv[2]), int(sys.argv[3])
width = os.get_terminal_size().columns
date_day, date_month, date_days = 10, 8, 90 # day and month of data, how many days
asset = '{}-{}_{}_d{}_{}'.format(date_day, date_month, asset_name, date_days, currency)	
agent = Agent(window_size)
#------------------------------------------------------------->
print(chr(27) + "[2J")
#------------------------------------------------------------->
for e in range(episode_count+1):
    operate(
        agent=agent,
        asset_name=asset_name,
        model_name=False,
        window_size=window_size
    )
    print(colored("Episode {}/{} - Window size {}".format(str(e),str(episode_count), window_size).center(width),'cyan',attrs=['bold']))
    if e % 10 == 0:
        agent.model.save("models/{}-{}_{}_d{}_e{}_w{}_c{}_{}".format(date_day, date_month, asset_name,date_days, str(e), window_size, episode_count, currency))
print(colored('D O N E'.center(width),'white','on_green',attrs=['bold']),'\n\n')