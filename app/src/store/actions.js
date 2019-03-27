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
          let date = new Date(obj[key].time * 1000)
          labels.push(date.getHours() + 'h')
          series.push(obj[key].close)
        }
        commit('setDashboardDataLabels', labels)
        commit('setDashboardDataSeries', series)
        commit('setLoading', false)
      })
  }
}
