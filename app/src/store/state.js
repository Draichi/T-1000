// https://vuex.vuejs.org/en/state.html

export default {
  loading: false,
  BTCMinute: {
    data: {
      labels: [],
      series: [
        []
      ]
    },
    options: {
      axisX: {
        showLabel: false
      }
    }
  },
  BTCHourly: {
    data: {
      labels: [],
      series: [
        []
      ]
    }
  },
  dataCompletedTasksChart: {
    data: {
      labels: ['12am', '3pm', '6pm', '9pm', '12pm', '3am', '6am', '9am'],
      series: [
        [230, 750, 450, 300, 280, 240, 200, 190],
        [130, null, null, 300, null, null, 200, NaN]
      ]
    }
  },
  emailsSubscriptionChart: {
    data: {
      labels: ['Ja', 'Fe', 'Ma', 'Ap', 'Mai', 'Ju', 'Jul', 'Au', 'Se', 'Oc', 'No', 'De'],
      series: [
        [542, 443, 320, 780, 553, 453, 326, 434, 568, 610, 756, 895]
      ]
    },
    responsiveOptions: [
      ['screen and (max-width: 640px)', {
        seriesBarDistance: 5,
        axisX: {
          labelInterpolationFnc: function (value) {
            return value[0]
          }
        }
      }]
    ]
  }
}
