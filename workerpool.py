import threading, requests, time
from configs.vars import coins
import pandas as pd
start = time.time()

def fetch_url(coin):
    print('-- downloading {}'.format(coin))
    url = "https://api.coingecko.com/api/v3/coins/{}/market_chart?vs_currency=btc&days=10".format(coin)
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    df = pd.DataFrame(response.json())
    df.to_csv('datasets/thread-{}.csv'.format(coin), index=False)
    print("---{} fetched and cached in {}% s".format(coin, (time.time() - start)))

threads = [threading.Thread(target=fetch_url, args=(coin,)) for coin in coins]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

print("Elapsed Time: {}".format(time.time() - start))
