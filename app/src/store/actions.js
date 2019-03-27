// https://vuex.vuejs.org/en/actions.html
// https://stackoverflow.com/questions/47916630/async-await-actions-in-vuex

// TODO:
// - ver se funciona o request async
// - tirar o tratamneto da res de detro do 'then' bloco

import axios from 'axios'

export default {
  async loadDashboadData ({commit}) {
    commit('setLoading', true)
    try {
      let res = await axios.get(
        'https://min-api.cryptocompare.com/data/histominute?fsym=BTC&tsym=USD&e=Coinbase&limit=20',
        {headers: {
          authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
        }}
      )
      const labels = []
      const series = []
      const obj = res.data.Data
      for (let key in obj) {
        // let date = new Date(obj[key].time * 1000)
        // labels.push(date.getMinutes() + 'h')
        labels.push(key)
        series.push(obj[key].close)
      }
      commit('setDashboardDataLabels', labels)
      commit('setDashboardDataSeries', series)
      commit('setLoading', false)
    } catch (e) {
      console.log(e)
    }
  }
}
