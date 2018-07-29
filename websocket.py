from lomond import WebSocket
import json
# pip2 install lomond
thefile = open('test.txt', 'w')
websocket = WebSocket('wss://ws-feed.gdax.com')
data = []
for event in websocket:
    if event.name == "ready":
        websocket.send_json(
            type='subscribe',
            product_ids=['BTC-USD'],
            channels=['ticker']
        )
    elif event.name == "text":
        res = event.json
        # data = json.loads(res)
        # for i in enumerate(res):
        #     print(i)
        thefile.write("%s\n" % res)
        # data.append(res)
        # print(res)
        # print(data)