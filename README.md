![python](https://forthebadge.com/images/badges/made-with-python.svg "python")

# Cryptocurrency prediction

Deep tecnical analysis with **ANY** cryptocurrency

## Setup

Go to `configs/vars` and edit these lines:
```python
coins = ['bitcoin','nano','binancecoin','steem']
days = 90
currency = 'usd'
```
---
## Run

```sh
git clone https://github.com/Draichi/cryptocurrency_prediction.git
cd cryptocurrency_prediction
mkdir models
mkdir datasets
pip3 install -r requirements.txt
python3 lin.py
# python3 log.py to see in logarithm scale
python3 forecast.py [asset]
# e.g.: python3 forecast bitcoin
```
![10-8-2018](imgs/bitcoin90days.png "10-8-2018")

Forecast:
![10-8-2018](imgs/bitcoin_forecast.png "10-8-2018")

Zoom:
![10-8-2018](imgs/bitcoin_zoon.png "10-8-2018")

Forecast:
![10-8-2018](imgs/bitcoin.png "10-8-2018")

## Credits
- [Analyzing](https://blog.patricktriest.com/analyzing-cryptocurrencies-python/) cryptocurrency markets using python