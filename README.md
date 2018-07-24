# Bot Advisor

Bot advisor using machine learning to give insights about market movements

![python](https://forthebadge.com/images/badges/made-with-python.svg "python")
![lin](imgs/lin.png "linear")
![log](imgs/log.png "log")
![heatmap](imgs/heatmap.png "heatmap")
![predict](imgs/prediction.png "predict")

## Setup

```sh
pip3 install -r requirements.txt

python3 lin.py
# a window will pop-up with the chart

python3 log.py
# a window will pop-up with the chart

python3 heat.py --year 2017
# a window will pop-up with the chart

python3 predict.py --days 7 --change 0.02 --coin BTC
# 'Spread prediciton' will tell what you should do

```

as we have 3 options (hold, buy, sell) accuracy is calculated different, 33% accuracy means randomness, we difficult will get more than 70%
