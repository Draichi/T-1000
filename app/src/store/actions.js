// https://vuex.vuejs.org/en/actions.html

import axios from 'axios'

function getTimeseries (state) {
  let timeseries = {}
  for (let key in state.symbolData) {
    if (state.symbolData[key].checkbox === true) {
      var obj = state.symbolData[key]
      var date = obj.data.labels
      timeseries['date'] = date
      // var coin = obj.info.CoinInfo.Name
      var fromSymbol = obj.info.RAW[Object.keys(obj.info.RAW)[0]].FROMSYMBOL
      var toSymbol = obj.info.RAW[Object.keys(obj.info.RAW)[0]].TOSYMBOL
      var price = obj.data.series[0]
      timeseries[fromSymbol + toSymbol] = price
    }
  }
  return timeseries
}

function getEachCoin (commit, state, info) {
  var firstIndex = Object.keys(info.DISPLAY)[0]
  var fromSymbol = info.RAW[firstIndex].FROMSYMBOL
  var toSymbol = info.RAW[firstIndex].TOSYMBOL
  var pair = fromSymbol + toSymbol
  axios.get(`https://min-api.cryptocompare.com/data/histo${state.history}?fsym=${fromSymbol}&tsym=${toSymbol}&limit=${state.timeseriesItens}&e=Binance`,
    {
      headers: {
        authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
      }
    })
    .then(res => {
      if (res.data.Response !== 'Success') { return }
      var response = {
        botFood: {
          pair: pair,
          open: [],
          high: [],
          low: [],
          close: [],
          volume: [],
          time: []
        },
        data: {
          labels: [],
          series: [[]]
        },
        checkbox: false,
        info: info
      }
      var obj = res.data.Data
      for (let key in obj) {
        var i = obj[key]
        let date = new Date(i.time * 1000)
        response.data.labels.push(date)
        response.data.series[0].push(i.close)

        response.botFood.open.push(i.open)
        response.botFood.high.push(i.high)
        response.botFood.low.push(i.low)
        response.botFood.close.push(i.close)
        response.botFood.volume.push(i.volumefrom)
        response.botFood.time.push(i.time)
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
  getTopCapCoins ({commit, state}) {
    commit('setLoading', true)
    let currencyList = ['BTC', 'USDT', 'BNB', 'ETH']
    for (var i in currencyList) {
      axios.get(`https://min-api.cryptocompare.com/data/top/mktcapfull?limit=${state.coinsToShow}&tsym=${currencyList[i]}`,
        {
          headers: {
            authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
          }
        })
        .then(res => {
          var obj = res.data.Data
          for (let key in obj) {
            var info = obj[key]
            getEachCoin(commit, state, info)
          }
        })
        .catch(e => {
          commit('setError', e)
          console.warn(e)
        })
    }
    // axios.get(`https://min-api.cryptocompare.com/data/top/mktcapfull?limit=${state.coinsToShow}&tsym=BTC`,
    //   {
    //     headers: {
    //       authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
    //     }
    //   })
    //   .then(res => {
    //     var obj = res.data.Data
    //     commit('setTopCoinsTable', obj)
    //     for (let key in obj) {
    //       var info = obj[key]
    //       getEachCoin(commit, state, info)
    //     }
    //   })
    //   .catch(e => {
    //     commit('setError', e)
    //     console.warn(e)
    //   })
    // axios.get(`https://min-api.cryptocompare.com/data/top/mktcapfull?limit=${state.coinsToShow}&tsym=BNB`,
    //   {
    //     headers: {
    //       authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
    //     }
    //   })
    //   .then(res => {
    //     var obj = res.data.Data
    //     for (let key in obj) {
    //       var info = obj[key]
    //       getEachCoin(commit, state, info)
    //     }
    //   })
    //   .catch(e => {
    //     commit('setError', e)
    //     console.warn(e)
    //   })
    // axios.get(`https://min-api.cryptocompare.com/data/top/mktcapfull?limit=${state.coinsToShow}&tsym=ETH`,
    //   {
    //     headers: {
    //       authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
    //     }
    //   })
    //   .then(res => {
    //     var obj = res.data.Data
    //     for (let key in obj) {
    //       var info = obj[key]
    //       getEachCoin(commit, state, info)
    //     }
    //   })
    //   .catch(e => {
    //     commit('setError', e)
    //     console.warn(e)
    //   })
    // axios.get(`https://min-api.cryptocompare.com/data/top/mktcapfull?limit=${state.coinsToShow}&tsym=USDT`,
    //   {
    //     headers: {
    //       authorization: '3d7d3e9e6006669ac00584978342451c95c3c78421268ff7aeef69995f9a09ce'
    //     }
    //   })
    //   .then(res => {
    //     var obj = res.data.Data
    //     for (let key in obj) {
    //       var info = obj[key]
    //       getEachCoin(commit, state, info)
    //     }
    //   })
    //   .catch(e => {
    //     commit('setError', e)
    //     console.warn(e)
    //   })
    commit('setLoading', false)
  },
  sendPortfolioRetunsReq ({state}) {
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
  // sendPortfolioCorrelationReq ({commit, state}) {
  //   let timeseries = getTimeseries(state)
  //   axios.post('http://localhost:3030/correlation',
  //     {
  //       // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
  //       'timeseries': timeseries
  //     })
  //     .then(res => {
  //       state.snackbar = true
  //       state.snackbarMsg = res.data
  //     })
  // },
  // sendPortfolioEfficientFrontierReq ({commit, state}) {
  //   let timeseries = getTimeseries(state)
  //   axios.post('http://localhost:3030/efficient_frontier',
  //     {
  //       // 'headers': {'Content-Encoding': 'gzip', 'Access-Control-Allow-Origin': '*'},
  //       'timeseries': timeseries
  //     })
  //     .then(res => {
  //       state.snackbar = true
  //       state.snackbarMsg = res.data
  //     })
  // },
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
