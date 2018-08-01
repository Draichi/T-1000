import threading, requests, time, os
from configs.vars import coins, days, todays_month, todays_day
import pandas as pd
start = time.time()

def fetch_url(coin):
    if not (os.path.exists('datasets/{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days))):
        print('-- downloading {}, {} days dataset, this will take a while'.format(coin, days))
        url = "https://api.coingecko.com/api/v3/coins/{}/market_chart?vs_currency=btc&days={}".format(coin, days)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        df = pd.DataFrame(response.json())
        df.to_csv('datasets/{}-{}-{}_{}-days.csv'.format(coin, todays_day, todays_month, days), index=False)
        print("---{} fetched and cached in {} seconds".format(coin, (time.time() - start)))
    else:
        print('-- loading {} from cache'.format(coin))

threads = [threading.Thread(target=fetch_url, args=(coin,)) for coin in coins]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
