from urllib import  request
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize
import ad, math, random, glob

def bonds_data():
    data = []
    for year in ['2013', '2014', '2015', '2016', '2017']:
        path = 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/XmlView.aspx?data=yieldyear&year='+year
        html = request.urlopen(path)
        response = html.read().decode('utf-8')
        soup = BeautifulSoup(response, 'html.parser')
        elememts = soup.find_all('content', type="application/xml")
        for el in elememts:
            z = el.findChildren()
            data.append([z[2].string, z[6].string])
    df = pd.DataFrame(data, columns=['Date', 'price'])
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.to_csv('bonds.csv', sep=',', index=False, encoding='utf-8')

# Excpected Returns
def calc_exp_returns(avg_returns, weights):
    exp_returns = avg_returns.dot(weights.T)
    return exp_returns

# Variance-covariance matrix
def var_cov_matrix(df, weights):
    sigma = np.cov(np.array(df).T, ddof=0)  # Covariance
    var = (np.array(weights) * sigma * np.array(weights).T).sum()
    return var

def optimize():
    bounds = ((0.0, 1.),) * 5  # Bounds of the problem
    # [100%, 80%, 40% ... 0.1%]  return
    # exp_return_constraint = [1.0, 0.8, 0.4, 0.3, 0.2, 0.1, 0.01, 0.009, 0.008, 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001]
    exp_return_constraint = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
    results_comparison_dict = {}
    for i in range(len(exp_return_constraint)):
        res = minimize(
            # Objective function defined here
            lambda x: var_cov_matrix(df, x),
            weights, method='SLSQP'
            # Jacobian using automatic differentiation
            , jac=ad.gh(lambda x: var_cov_matrix(df, x))[0]
            # bounds given above
            , bounds=bounds, options={'disp': True, 'ftol': 1e-20, 'maxiter': 1000}
            , constraints=[{'type': 'eq', 'fun': lambda x: sum(x) - 1.0},
                           {'type': 'eq', 'fun': lambda x: calc_exp_returns(returns, x) - exp_return_constraint[i]}])
        returns_key = round(exp_return_constraint[i]*100, 2)
        results_comparison_dict.update({returns_key: [res.fun, res.x]})
    return res, results_comparison_dict


def plot_returns(df):
    f = plt.figure(figsize=(10, 10)) # Change the size as necessary
    df.plot(ax=f.gca()) # figure.gca means "get current axis"
    plt.title('Returns of assets', color='black')
    plt.savefig('returns.jpg')
    plt.show()


# PLOT SCATTER PLOT FOR EFFICIENT FRONTIER
def plot_efficient_frontier(comparison):
    z = [[x, comparison[x][0]*100] for x in comparison]
    # z = list(sorted(z, key=lambda x: x[1]))
    objects, risk_vals =  list(zip(*z))
    y_pos = np.arange(len(objects))
    plt.scatter(  risk_vals, objects)
    plt.xlabel('Risk (%)')
    plt.ylabel('Expected Returns (%)')
    plt.title('Risk associated with different levels of returns')
    plt.show()


# BAR CHART OF ASSETS WEIGHTS AT DIFFERENT EXPECTED RETURNS
def plot_weights_per_asset(comparison):
    assets = ['bonds',	'forex', 'bitcoin',	'gold',	'nyse']
    y_pos = np.arange(len(assets))
    keys = list(sorted(list(comparison.keys())))
    colors = ['red', 'b', 'g', 'k', 'm', 'y', 'c', 'coral']
    index = 0
    plt.figure(0)
    for i in range(4):
        for j in range(4):
            if (index == len(keys)): break
            ax = plt.subplot2grid((4, 4), (i, j))
            ax.bar(y_pos, comparison[keys[index]][1], align='center', alpha=0.5, color=random.choice(colors))
            ax.set_xticklabels(['']+assets)
            ax.tick_params(axis='x', labelsize=8)
            ax.legend([keys[index]])
            index += 1
    plt.show()

if __name__ == '__main__':
    path = './data.csv'
    df = pd.read_csv(path)
    # Setting and cleaning up data
    df = df.set_index('Date')
    df = df.pct_change()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    returns = df.mean()
    # Initialize random weights
    np.random.seed(34522)
    weights =  np.random.dirichlet(np.ones(5),size=1) # makes sure that weights sums upto 1.
    # PORTFOLIO OPTIMIZATION AND RESULTS
    res, comparison = optimize()

    plot_efficient_frontier(comparison)
    plot_weights_per_asset(comparison)