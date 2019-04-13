// https://vuex.vuejs.org/en/mutations.html
import axios from 'axios'

export default {
  setLoading (state, payload) {
    state.loading = payload
  },
  setError (state, payload) {
    state.error = payload
  },
  clearError (state) {
    state.error = null
  },
  setTopVolCoins (state, payload) {
    state.topVolCoins = payload
  },
  addSymbolData (state, payload) {
    state.symbolData.push(payload)
  },
  sendProphetReq (state, payload) {
    var coins = state.symbolData
    for (let key in coins) {
      if (coins[key].coin === payload.symbol) {
        axios.post('http://localhost:3030/prophet',
          {
            // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
            'dataset': {'ds': coins[key].data.labels, 'y': coins[key].data.series[0]},
            'changepoint_prior_scale': payload.changepoint,
            'forecast_days': payload.forecast,
            'symbol': payload.symbol
          })
          .then(res => {
            console.log(res)
            state.snackbar = true
            state.snackbarMsg = res.data
          })
          .catch(e => {
            state.snackbar = true
            state.snackbarMsg = e.data
            console.log('errosssss:',String(e))
          })
      }
    }
  },
  setEpisodeRewardMax(state, payload) {
    state.episodeRewardMax = payload
  }
}
