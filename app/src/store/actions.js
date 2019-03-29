// https://vuex.vuejs.org/en/actions.html

import axios from 'axios'

export default {
  async getBTCMinute ({commit}) {
    commit('setLoading', true)
    try {
      let res = await axios.get(
        'https://min-api.cryptocompare.com/data/histominute?fsym=BTC&tsym=USD&e=Coinbase&limit=20',
        {headers: {
          authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
        }}
      )
      const data = {labels: [], series: [[]]}
      const obj = res.data.Data
      for (let key in obj) {
        let date = new Date(obj[key].time * 1000)
        data.labels.push(date.getMinutes())
        data.series[0].push(obj[key].close)
      }
      commit('setBTCMinute', data)
      commit('setLoading', false)
    } catch (e) {
      console.warn(e)
    }
  },
  async getBTCHourly ({commit}) {
    commit('setLoading', true)
    try {
      let res = await axios.get(
        'https://min-api.cryptocompare.com/data/histohour?fsym=BTC&tsym=USD&e=Coinbase&limit=20',
        {headers: {
          authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
        }}
      )
      const data = {labels: [], series: [[]]}
      const obj = res.data.Data
      for (let key in obj) {
        let date = new Date(obj[key].time * 1000)
        data.labels.push(date)
        data.series[0].push(obj[key].close)
      }
      commit('setBTCHourly', data)
      commit('setLoading', false)
    } catch (e) {
      console.warn(e)
    }
  },
  sendProphetReq ({commit}) {
    // return console.log(this.state.BTCHourly.data.labels, this.state.BTCHourly.data.series[0])
    axios.post('http://localhost:3030/prophet',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        'dataset': {'ds': this.state.BTCHourly.data.labels, 'y': this.state.BTCHourly.data.series[0]},
        'changepoint_prior_scale': 0.05,
        'forecast_days': 1
      })
      .then(res => console.log(res))
    // commit('setLoading', true)
  }
}
