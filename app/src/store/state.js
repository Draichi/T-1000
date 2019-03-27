// https://vuex.vuejs.org/en/state.html

export default {
  loading: false,
  dailySalesChart: {
    data: {
      labels: [],
      series: [
        []
      ]
    },
  },
  dataCompletedTasksChart: {
    data: {
      labels: ['12am', '3pm', '6pm', '9pm', '12pm', '3am', '6am', '9am'],
      series: [
        [230, 750, 450, 300, 280, 240, 200, 190],
        [130, 550, 350, 200, 380, 140, 300, 90],
      ]
    },
  }
}
