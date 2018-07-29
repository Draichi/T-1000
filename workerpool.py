import threading, urllib3, time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

start = time.time()
urls = [
    "https://api.coingecko.com/api/v3/coins/litecoin/market_chart?vs_currency=btc&days=60",
    "https://api.coingecko.com/api/v3/coins/nano/market_chart?vs_currency=btc&days=60",
    "https://api.coingecko.com/api/v3/coins/steem/market_chart?vs_currency=btc&days=60",
]

def fetch_url(url):
    print('-- downloading {}'.format(url))
    http = urllib3.PoolManager()
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = http.request('GET', url, headers=headers)
    html = r.data
    print("{} fetched in {}s".format(url, (time.time() - start)))

threads = [threading.Thread(target=fetch_url, args=(url,)) for url in urls]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

print("Elapsed Time: {}".format(time.time() - start))
