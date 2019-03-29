// https://vuex.vuejs.org/en/mutations.html

export default {
  setLoading (state, payload) {
    state.loading = payload
  },
  setBTCMinute (state, payload) {
    state.BTCMinute.data = payload
  },
  setBTCHourly (state, payload) {
    state.BTCHourly.data = payload
  },
}
