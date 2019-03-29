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
  setETHBTC (state, payload) {
    state.ETHBTCData = payload
  }
}
