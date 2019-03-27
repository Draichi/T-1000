// https://vuex.vuejs.org/en/actions.html
import axios from 'axios'

export default {
  loadDashboadData ({commit}) {
    commit('setLoading', true)
    axios.get('https://min-api.cryptocompare.com/data/histohour?fsym=BTC&tsym=USD&e=Coinbase&limit=10',
      {headers: {authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'}})
      .then(res => {
        const labels = []
        const series = []
        const obj = res.data.Data
        for (let key in obj) {
          labels.push(key)
          series.push(obj[key].close)
        }
        commit('setDashboardDataLabels', labels)
        commit('setDashboardDataSeries', series)
        // console.log('data actions')
        // console.log(data)
        commit('setLoading', false)
      })
  }
}
