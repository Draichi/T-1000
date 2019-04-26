// https://vuex.vuejs.org/en/mutations.html
import axios from 'axios'

function getTimeseriesFullData (state) {
  let timeseries = {}
  for (let key in state.symbolData) {
    if (state.symbolData[key].checkbox === true) {
      var obj = state.symbolData[key]
      // var date = obj.data.labels
      // timeseries['date'] = date
      // // var coin = obj.info.CoinInfo.Name
      // var fromSymbol = obj.info.RAW[Object.keys(obj.info.RAW)[0]].FROMSYMBOL
      // var toSymbol = obj.info.RAW[Object.keys(obj.info.RAW)[0]].TOSYMBOL
      // var price = obj.data.series[0]
      timeseries[obj.botFood.pair + '_open'] = obj.botFood.open
      timeseries[obj.botFood.pair + '_high'] = obj.botFood.high
      timeseries[obj.botFood.pair + '_low'] = obj.botFood.low
      timeseries[obj.botFood.pair + '_close'] = obj.botFood.close
      timeseries[obj.botFood.pair + '_volume'] = obj.botFood.volume
      timeseries['time'] = obj.botFood.time
    }
  }
  return timeseries
}

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
  setTopCoinsTable (state, payload) {
    state.topCoinsTable = payload
  },
  addSymbolData (state, payload) {
    state.symbolData.push(payload)
  },
  sendProphetReq (state, payload) {
    var coins = state.symbolData
    for (let key in coins) {
      if (coins[key].botFood.pair == payload.symbol) {
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
            console.log('errosssss:', String(e))
          })
      }
    }
  },
  sendIndicatorsReq (state, payload) {
    let timeseriesFullData = getTimeseriesFullData(state)
    axios.post('http://localhost:3030/indicatorsDashboard',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        // 'timeseries': state.symbolData[item].botFood
        'timeseries': timeseriesFullData
      })
    return
    for (var item in state.symbolData) {
      if (state.symbolData[item].botFood.pair === payload.symbol) {
        axios.post('http://localhost:3030/indicatorsDashboard',
          {
            // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
            // 'timeseries': state.symbolData[item].botFood
            'timeseries': timeseriesFullData
          })
          .then(res => {
            console.log(res)
            state.snackbar = true
            state.snackbarMsg = res.data
          })
          .catch(e => {
            state.snackbar = true
            state.snackbarMsg = e.data
            console.log('errosssss:', String(e))
          })
      }
    }
  },
  setEpisodeRewardMax (state, payload) {
    state.episodeRewardMax = payload
  }
}
