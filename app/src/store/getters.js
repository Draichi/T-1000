// https://vuex.vuejs.org/en/getters.html

export default {
  loading (state) {
    return state.loading
  },
  dataCompletedTasksChart (state) {
    return state.dataCompletedTasksChart
  },
  dailySalesChart (state) {
    return state.dailySalesChart
  },
  emailsSubscriptionChartGraph (state) {
    return state.emailsSubscriptionChart
  }
}
