// https://vuex.vuejs.org/en/mutations.html

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
  }
}
