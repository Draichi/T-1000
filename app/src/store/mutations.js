// https://vuex.vuejs.org/en/mutations.html

export default {
  setLoading (state, payload) {
    state.loading = payload
  },
  setDashboardDataLabels (state, payload) {
    state.dailySalesChart.data.labels = payload
  },
  setDashboardDataSeries (state, payload) {
    state.dailySalesChart.data.series[0] = payload
  }
}
