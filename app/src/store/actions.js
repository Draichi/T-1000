// https://vuex.vuejs.org/en/actions.html

import axios from 'axios'

function getTimeseries (state) {
  let timeseries = {}
  for (let key in state.symbolData) {
    if (state.symbolData[key].checkbox === true) {
      var obj = state.symbolData[key]
      var date = obj.data.labels
      timeseries['date'] = date
      var coin = obj.coin
      var price = obj.data.series[0]
      timeseries[coin] = price
    }
  }
  return timeseries
}

function getEachCoin (commit, symbol) {
  axios.get(`https://min-api.cryptocompare.com/data/histoday?fsym=${symbol}&tsym=BTC&limit=800`,
    {
      headers: {
        authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
      }
    })
    .then(res => {
      var response = {coin: symbol, data: {labels: [], series: [[]]}, checkbox: false}
      var obj = res.data.Data
      for (let key in obj) {
        let date = new Date(obj[key].time * 1000)
        response.data.labels.push(date)
        response.data.series[0].push(obj[key].close)
      }
      commit('addSymbolData', response)
    })
    .catch(e => {
      commit('setError', e)
      console.warn(e)
    })
}

function csvJSON (csv) {
  var lines = csv.split('\n')
  var result = {labels: [], series: [[]]}
  for (var i = 1; i < lines.length - 1; i++) {
    var currentline = lines[i].split(',')
    result.labels.push(currentline[1])
    result.series[0].push(currentline[2])
  }
  return JSON.stringify(result)
}

export default {
  getTopVolCoins ({commit}) {
    commit('setLoading', true)
    axios.get('https://min-api.cryptocompare.com/data/top/volumes?tsym=BTC&limit=25',
      {
        headers: {
          authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
        }
      })
      .then(res => {
        var obj = res.data.Data
        commit('setTopVolCoins', obj)
        for (let key in obj) {
          var symbol = obj[key].SYMBOL
          getEachCoin(commit, symbol)
        }
      })
      .catch(e => {
        commit('setError', e)
        console.warn(e)
      })
    commit('setLoading', false)
  },
  sendPortfolioRetunsReq ({commit, state}) {
    let timeseries = getTimeseries(state)
    axios.post('http://localhost:3030/returns',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        'timeseries': timeseries
      })
      .then(res => {
        state.snackbar = true
        state.snackbarMsg = res.data
      })
  },
  sendPortfolioCorrelationReq ({commit, state}) {
    let timeseries = getTimeseries(state)
    axios.post('http://localhost:3030/correlation',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        'timeseries': timeseries
      })
      .then(res => {
        state.snackbar = true
        state.snackbarMsg = res.data
      })
  },
  sendPortfolioEfficientFrontierReq ({commit, state}) {
    let timeseries = getTimeseries(state)
    axios.post('http://localhost:3030/efficient_frontier',
      {
        // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
        'timeseries': timeseries
      })
      .then(res => {
        state.snackbar = true
        state.snackbarMsg = res.data
      })
  },
  getTradingBotStats ({commit, state}) {
    commit('setLoading', true)
    axios.get('https://raw.githubusercontent.com/Draichi/cryptocurrency_prediction/master/datasets/episode_reward_max.csv')
      .then(res => {
        var obj = csvJSON(res.data)
        var series = JSON.parse(obj)
        commit('setEpisodeRewardMax', series)
      })
      .catch(e => {
        commit('setError', e)
        console.warn(e)
      })
    commit('setLoading', false)
  }
}
