import plotly.graph_objs as go
import plotly.offline as offline

def correlation_heatmap(df, title, absolute_bounds=True):
    '''plot a correlation heatmap for the entire dataframe'''
    heatmap = go.Heatmap(
        z=df.corr(method='pearson').values,
        x=df.columns,
        y=df.columns,
        colorbar=dict(title='Pearson Coefficient')
    )
    layout = go.Layout(
        title=title,
        plot_bgcolor='#010008',
        paper_bgcolor='#010008',
        font=dict(color='rgb(255, 255, 255)')
    )

    if absolute_bounds:
        heatmap['zmax'] = 1.0
        heatmap['zmin'] = -1.0

    offline.plot(
        {
            'data': [heatmap],
            'layout': layout
        }, 
        image = None,
        filename = '{}.html'.format(title.replace(" ", "_")),
        image_filename = title
    )