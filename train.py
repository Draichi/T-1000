import sys
from termcolor import colored
if len(sys.argv) != 4:
	print(colored("Usage: python3 train.py [asset] [window] [episodes]", 'red', attrs=['bold']))
	exit()
import os, configs.get_datasets
from configs.agent import Agent
from configs.functions import *
from configs.vars import days, currency, todays_day, todays_month, batch_size, terminal_width
#------------------------------------------------------------->
asset_name, window_size, episode_count = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
agent = Agent(window_size)
#------------------------------------------------------------->
print(chr(27) + "[2J")
#------------------------------------------------------------->
for e in range(episode_count+1):
    print('\n')
    print(colored('~'.center(terminal_width),'cyan'))
    print(colored("EPISODE {}/{}:".format(str(e),str(episode_count)).center(terminal_width),'magenta',attrs=['bold']))
    operate(
        agent=agent,
        asset_name=asset_name,
        model_name=False,
        window_size=window_size
    )
    if e % 50 == 0:
        agent.model.save("models/{}-{}_{}_d{}_e{}_w{}_c{}_{}".format(todays_day,todays_month,asset_name,days,str(e),window_size,episode_count,currency))
print('\n\n',colored('D O N E'.center(terminal_width),'white','on_green',attrs=['bold']))