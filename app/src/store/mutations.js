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
  setETHBTC (state, payload) {
    state.ETHBTCData = payload
  },
  setXRPBTC (state, payload) {
    state.XRPBTCData = payload
  },
  setEOSBTC (state, payload) {
    state.EOSBTCData = payload
  },
  setLTCBTC (state, payload) {
    state.LTCBTCData = payload
  }
}
