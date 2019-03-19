![ubuntu](https://img.shields.io/badge/ubuntu-supported-000.svg?colorA=00cc25&longCache=true&style=for-the-badge "ubuntu")
![windows](https://img.shields.io/badge/windows-supported-000.svg?colorA=00cc25&longCache=true&style=for-the-badge "windows")
![OS](https://img.shields.io/badge/OS-supported-000.svg?colorA=00cc25&longCache=true&style=for-the-badge "OS")

# Cryptocurrency prediction

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ebdf89dcba744a3c8aafdda210d3aeb6)](https://app.codacy.com/app/Draichi/cryptocurrency_prediction?utm_source=github.com&utm_medium=referral&utm_content=Draichi/cryptocurrency_prediction&utm_campaign=Badge_Grade_Dashboard)

Deep tecnical analysis with [**ANY**](https://www.coingecko.com/en) cryptocurrency

See also this live [demo](https://bud-fox.github.io/live/)

## Prerequisites

-   [Miniconda](https://conda.io/docs/user-guide/install/index.html) or Anaconda

## Setup

Go to `configs/vars` and edit these lines:

```python
PORTFOLIO_SYMBOLS = [
    'eth',
    'xrp',
    'ltc'
]
TIME_INTERVAL = '1d'
FROM_DATE = '2018-11-01'
TO_DATE = '2019-03-18'
```

* * *

### Ubuntu

```sh
sudo apt-get install gcc g++ build-essential python-dev python3-dev
# make sure you have these installed
conda env create -f UBUNTU_CPU.yml
# create env
```

### Windows

```sh
# make sure you have a recent C++ compiler
conda env create -f WINDOWS_CPU.yml
# create env
```

### Mac

```sh
conda env create -f MAC_CPU.yml
# create env
```

* * *

```sh
python plot_portfolio.py --plot_coin [COIN_NAME]
# e.g.: python plot_portfolio.py --plot_coin eth
# open the /path/to/crytocurrency_prediction/temp-plot.html file
```

![imgs/dashboard_demo.gif ](imgs/dashboard_demo.gif )

## Live demos

-   [Dashboard LTC Momentum](https://draichi.github.io/cryptocurrency_prediction/dashboard_ltc_momentum.html)
-   [Dashboard LTC Hype](https://draichi.github.io/cryptocurrency_prediction/dashboard_ltc_hype.html)
-   [Dashboard LTC Prophet](https://draichi.github.io/cryptocurrency_prediction/dashboard_LTC_prophet.html)
-   [Portfolio Weigths](https://draichi.github.io/cryptocurrency_prediction/weights.html)
-   [Kendall Correlation](https://draichi.github.io/cryptocurrency_prediction/kendall_correlation.html)
-   [efficient_frontier](https://draichi.github.io/cryptocurrency_prediction/efficient_frontier.html)



<!-- * * *

## DQN

```sh
python train.py [asset] [window_size] [how_many_episodes]
# e.g.: python3 train.py bitcoin 10 1000
```

![trainning](imgs/trainning.gif)

Use historical data to train a model and evaluate with fresh data

```sh
python evaluate.py [asset] [model]
# e.g.: python3 evaluate.py bitcoin 10-8_bitcoin_d90_e20_w12_c50_usd
```

![evaluate](imgs/evaluating.gif)

Price in: blue = buy, yellow = sell, white = hold -->

* * *

## Credits

-   Analyzing cryptocurrency markets using python: [article](https://blog.patricktriest.com/analyzing-cryptocurrencies-python/)
-   Q-trader: [repo](https://github.com/edwardhdlu/q-trader)
