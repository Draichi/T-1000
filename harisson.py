import pandas as pd
import numpy as np
from sklearn import preprocessing, cross_validation, svm
from sklearn.linear_model import LinearRegression
import datetime
from datetime import timedelta

df = pd.read_csv('datasets/df_steem_para_forecast.csv')

# for key in ['prices', 'total_volumes', 'market_caps']:
#     for i, item in enumerate(df[key]):
#         str_item = str(item)
#         current_item = str_item.replace('[', '').replace(']', '').split(',')
#         date = current_item[0]
#         price = current_item[1]
#         dt = datetime.datetime.fromtimestamp(int(date)/1000).strftime('%Y-%m-%d %H:%M:%S')
#         df.loc[i, 'date'] = dt
#         df.loc[i, key] = price
# df.set_index('date', inplace=True)
# df = pd.DataFrame(df)
# df.to_csv('datasets/df_steem_para_forecast.csv')
df['tomorow'] = df['prices'].shift(-1)
# df.dropna(inplace=True)
print(df.tail())
quit()
x = np.array(df[['prices', 'total_volumes', 'market_caps']])
y = np.array(df['tomorow'])
predict = np.array([[0.0002593170154753631, 915.4782093373011, 68739.44717154591]])
# 
# 2018-07-17 21:00:00, 115756.33225633256, 0.0004344068164714622, 5298.392504233303
# 2018-07-18 21:00:00, 92441.15650531855, 0.0003478047109758827, 2982.8144624025795
# 2018-07-19 21:00:00, 77820.66689029688, 0.0002936072282110834, 875.0922831525717
# 2018-07-20 21:00:00, 68739.44717154591, 0.0002593170154753631, 915.4782093373011
# 2018-07-21 21:00:00, 112000.8663204247, 0.0004220597336988911, 2333.1654983665985
# 2018-07-22 21:00:00, 96879.25872227014, 0.0003642321335252966, 1390.2556618922374
# 2018-07-23 21:00:00, 121735.94082815957, 0.00045739625435569324, 3648.3659746960075
# 2018-07-24 21:00:00, 45820.595413075585, 0.00017211249549131064, 532.78833101687
# 2018-07-25 06:53:19, 46734.928076094875, 0.00017554286758012755, 881.025316849226
#
x_train, x_test, y_train, y_test = cross_validation.train_test_split(x, y, test_size=0.2)

clf = LinearRegression()
clf.fit(x_train, y_train)
acc = clf.score(x_test, y_test)
prd = clf.predict(predict)
print(acc)
print(prd)

# data = df.iloc[-1].date
# data = data.split(' ')
# data = data[0].split('-')
# dia = datetime.date(int(data[0]), int(data[1]), int(data[2]))
# amanha = dia + timedelta(days=1)
    

