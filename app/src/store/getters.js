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
  },
  ETHBTCData (state) {
    return state.ETHBTCData
  },
  XRPBTCData (state) {
    return state.XRPBTCData
  },
  EOSBTCData (state) {
    return state.EOSBTCData
  },
  LTCBTCData (state) {
    return state.EOSBTCData
  }
}
