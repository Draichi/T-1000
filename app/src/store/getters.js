// https://vuex.vuejs.org/en/getters.html

export default {
  loading (state) {
    return state.loading
  },
  dataCompletedTasksChart (state) {
    return state.dataCompletedTasksChart
  },
  BTCMinute (state) {
    return state.BTCMinute
  },
  BTCHourly (state) {
    return state.BTCHourly
  },
  emailsSubscriptionChartGraph (state) {
    return state.emailsSubscriptionChart
  }
}
