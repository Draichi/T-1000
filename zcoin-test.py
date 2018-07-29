import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go
import urllib3, datetime
import pandas as pd
df = pd.read_csv('zcoin-test.csv', index_col=[0])
ju = ['zcoin','zcoin_1d','zcoin_2d','zcoin_3d','zcoin_4d','zcoin_5d','zcoin_6d','zcoin_7d']
data = []
for coin in ju:
    trace = go.Scatter(
        x=df.index,
        y=df[coin],
        name = coin,
    )
    data.append(trace)

layout = go.Layout(
    plot_bgcolor='#010008',
    paper_bgcolor='#010008',
    yaxis=dict(
        type='linear'
    )
)

offline.plot({'data': data, 'layout': layout})

