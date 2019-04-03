// https://vuex.vuejs.org/en/getters.html

export default {
  loading (state) {
    return state.loading
  },
  topVolCoins (state) {
    return state.topVolCoins
  },
  symbolData (state) {
    return state.symbolData
  }
}
