# import configs.get_datasets
import pandas as pd
import numpy as np
from configs.vars import coins, days, todays_day, todays_month, currency
# from configs.functions import print_dollar
import plotly.graph_objs as go
import plotly.offline as offline
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import ad, random
# import fbprophet

# TODO:
#   X fazer com que a correlation seja gerada qnd morkovitza for instanciado
#   - documentar as funcoes
#   X plotar com o plotly 
#   - tornnar o tamanho do plot dinamico em relaçao a quantidade de exp_return_constants

def calc_exp_returns(avg_return, weigths):
    exp_returns = avg_return.dot(weigths.T)
    return exp_returns

def var_cov_matrix(df, weigths):
    sigma = np.cov(np.array(df).T, ddof=0) # covariance
    var = (np.array(weigths) * sigma * np.array(weigths).T).sum()
    return var

def optimize():
    bounds = ((0.0, 1.),) * len(coins) # bounds of the problem
    # [0.7%, 0.6% , 0.5% ... 0.1%] returns
    exp_return_constraint = [ 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001, 0.0009, 0.0008, 0.0007, 0.0006, 0.0005,  0.0004, 0.0003, 0.0002, 0.0001]
    # exp_return_constraint = [ 0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06,0.05,0.04,0.03]
    results_comparison_dict = {}
    for i in range(len(exp_return_constraint)):
        res = minimize(
            # object function defined here
            lambda x: var_cov_matrix(df, x),
            weigths,
            method='SLSQP',
            # jacobian using automatic differentiation
            jac=ad.gh(lambda x: var_cov_matrix(df, x))[0],
            bounds=bounds,
            options={'disp': True, 'ftol': 1e-20, 'maxiter': 1000},
            constraints=[{'type': 'eq', 'fun': lambda x: sum(x) -1.0},
                         {'type': 'eq', 'fun': lambda x: calc_exp_returns(returns, x) - exp_return_constraint[i]}])
        return_key = round(exp_return_constraint[i]*100, 2)
        results_comparison_dict.update({return_key: [res.fun, res.x]})
    return res, results_comparison_dict

def plot_efficient_frontier(comparison):
    z = [[x, comparison[x][0]*100] for x in comparison]
    objects, risk_vals = list(zip(*z))
    t_pos = np.arange(len(objects))
    plt.scatter(risk_vals, objects)
    plt.xlabel('Risk %')
    plt.ylabel('Expected returns %')
    plt.title('Risk associated with different levels of returns')
    plt.show()

def plot_weights_per_asset(comparisson):
    y_pos = np.arange(len(coins))
    keys = list(sorted(list(comparisson.keys())))
    colors = ['red', 'b', 'g', 'k', 'm', 'y', 'c', 'coral']
    index = 0
    plt.figure(0)
    for i in range(4):
        for j in range(4):
            if (index == len(keys)): break
            ax = plt.subplot2grid((4,4), (i,j))
            ax.bar(y_pos, comparisson[keys[index]][1], align='center', alpha=0.5, color=random.choice(colors))
            ax.set_xticklabels(['']+coins)
            ax.tick_params(axis='x', labelsize=8)
            ax.legend([keys[index]])
            index += 1
    plt.show()

if __name__ == '__main__':
    np.random.seed(11123)
    weigths = np.random.dirichlet(alpha=np.ones(len(coins)), size=1) # makes sure that weights sums upto 1.
    # print(weigths)
    # quit()
    # print(weigths)
    # base_df = pd.read_csv('datasets/11-3_correlated_d90_btc.csv') # datasets/8-3_dash_d90_btc.csv
    df = pd.read_csv('datasets/11-3_correlated_d90_btc.csv') # datasets/8-3_dash_d90_btc.csv
    df = df.set_index('date')
    df = df.pct_change()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    df.to_csv('datasets/markovitz.csv')
    returns = df.mean()
    # PORTFOLIO OPTIMIZATION AND RESULTS
    res, comparison = optimize()

    plot_efficient_frontier(comparison)
    plot_weights_per_asset(comparison)