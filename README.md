![python](https://forthebadge.com/images/badges/made-with-python.svg "python")

# Cryptocurrency prediction

Deep tecnical analysis with **ANY** cryptocurrency

## Setup

Go to `configs/vars` and edit these lines:
```python
coins = ['giant','steem', 'nano', 'binancecoin', 'neo', 'bitshares',]
days = 365
```
---
## Run

```sh
git clone
cd bot_advisor
mkdir models
pip3 install -r requirements.txt
python3 lin.py
# python3 log.py to see in logarithm scale
python3 forecast.py [asset]
# e.g.: python3 forecast bitcoin
```
![10-8-2018](imgs/bitcoin90days.png "10-8-2018")
![10-8-2018](imgs/bitcoin_forecast.png "10-8-2018")
---
### Zoom
![10-8-2018](imgs/bitcoin_zoon.png "10-8-2018")
![10-8-2018](imgs/bitcoin.png "10-8-2018")
