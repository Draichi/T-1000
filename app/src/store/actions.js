// https://vuex.vuejs.org/en/actions.html

import axios from 'axios'

function axiosGet (commit, period, fsym, tsym, e, limit, seriesIdx, mutation) {
  commit('clearError')
  commit('setLoading', true)
  axios.get(`https://min-api.cryptocompare.com/data/${period}?fsym=${fsym}&tsym=${tsym}&e=${e}&limit=${limit}`,
    {
      headers: {
        authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
      }
    })
    .then(res => {
      var response = {labels: [], series: [[]]}
      var obj = res.data.Data
      for (let key in obj) {
        let date = new Date(obj[key].time * 1000)
        response.labels.push(date.getMinutes())
        response.series[seriesIdx].push(obj[key].close)
      }
      commit(mutation, response)
    })
    .catch(e => {
      commit('setError', e)
      console.warn(e)
    })
  commit('setLoading', false)
}

export default {
  getETHBTC ({commit}) {
    axiosGet(
      commit,
      'histohour',
      'ETH',
      'BTC',
      'Binance',
      '24',
      0,
      'setETHBTC'
    )
  },
  sendProphetReq ({commit}) {
    axios.post('http://localhost:3030/prophet',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        'dataset': {'ds': this.state.BTCHourly.data.labels, 'y': this.state.BTCHourly.data.series[0]},
        'changepoint_prior_scale': 0.05,
        'forecast_days': 1
      })
      .then(res => console.log(res))
  }
}
