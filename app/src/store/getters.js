// https://vuex.vuejs.org/en/getters.html

export default {
  loading (state) {
    return state.loading
  },
  symbolData (state) {
    return state.symbolData
  },
  topCoinsTable (state) {
    return state.topCoinsTable
  },
  episodeRewardMax (state) {
    return state.episodeRewardMax
  }
}
