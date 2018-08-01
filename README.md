# Bot Advisor

Bot advisor using machine learning to give insights about market movements

![python](https://forthebadge.com/images/badges/made-with-python.svg "python")

## Setup

Go to `configs/vars` and add what coins you want and how many days of data
```python
coins = ['giant','steem', 'nano', 'binancecoin', 'neo', 'bitshares',]
days = 365
```
---
```sh
pip3 install -r requirements.txt

python3 predict.py --days 7 --change 0.02 --coin bitcoin
```
![predict](imgs/prediction.png "predict")
---
```sh
python3 lin.py
```
![lin](imgs/lin.png "linear")
---
```sh
python3 log.py
# a window will pop-up with the chart
```
![log](imgs/log.png "log")
---
```sh
python3 heat.py --year 2017
```
![heatmap](imgs/heatmap.png "heatmap")
---

as we have 3 options (hold, buy, sell) accuracy is calculated different, 33% accuracy means randomness, we difficult will get more than 70%
