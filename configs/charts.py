import plotly.graph_objs as go
import plotly.offline as offline

def df_scatter(df, title, separate_y_axis=False, y_axis_label='', scale='linear', initial_hide=False):
    label_arr = list(df)
    series_arr = list(map(lambda col: df[col], label_arr))

    layout = go.Layout(
        plot_bgcolor='#010008',
        paper_bgcolor='#010008',
        title=title,
        font=dict(color='rgb(255, 255, 255)'),
        legend=dict(orientation="h"),
        xaxis=dict(type='date'),
        yaxis=dict(
            title=y_axis_label,
            showticklabels= not separate_y_axis,
            type=scale
        )
    )
    y_axis_config = dict(
        overlaying='y',
        showticklabels=False,
        type=scale
    )
    visibility = 'visible'
    if initial_hide:
        visibility = 'legendonly'
    # form trace for each series
    trace_arr = []
    for index, series in enumerate(series_arr):
        trace = go.Scatter(
            x=series.index,
            y=series,
            name=label_arr[index],
            visible=visibility
        )
        # add separate axis
        if separate_y_axis:
            trace['yaxis'] = 'y{}'.format(index + 1)
            layout['yaxis{}'.format(index + 1)] = y_axis_config
        
        trace_arr.append(trace)
    offline.plot(
        {
            'data': trace_arr, 
            'layout': layout
        },
        image = None,
        filename = '{}.html'.format(title.replace(" ", "_")),
        image_filename = title
    )

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