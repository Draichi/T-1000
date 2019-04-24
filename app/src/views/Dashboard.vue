<template>
  <v-container
    fill-height
    fluid
    grid-list-xl
  >
    <v-container
      v-show="loading"
      fluid>
      <v-layout row>
        <v-flex>
          <v-layout
            justify-center>
            <div class="text-xs-center">
              <v-progress-circular
                :color="colors"
                :size="80"
                indeterminate
              />
            </div>
          </v-layout>
        </v-flex>
      </v-layout>
    </v-container>
    <v-layout
      v-if="!loading"
      wrap
    >
      <!-- {{ symbolData }} -->
      <v-flex
        v-for="(symbol, indx) in symbolData"
        :key="indx"
        md12
        sm12
        lg4
      >
        <material-chart-card
          :data="symbol.data"
          :options="ChartsOptions"
          :color="colors"
          type="Line"
        >
          <h3 class="title font-weight-light">{{ symbol.info.CoinInfo.FullName }}</h3>
          <h4 class="title font-weight-light">{{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].FROMSYMBOL }} / {{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].TOSYMBOL }}</h4>
          <p class="category font-weight-light">Price: {{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].PRICE }}</p>
          <p class="category font-weight-light">Change 24h: {{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].CHANGE24HOUR }}</p>
          <p class="category font-weight-light">Total Volume 24h: {{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].TOTALVOLUME24HTO }}</p>
          <p class="category font-weight-light">Market Cap: {{ symbol.info.DISPLAY[Object.keys(symbol.info.DISPLAY)[0]].MKTCAP }}</p>
          <v-checkbox
            :label="(symbol.checkbox) ? 'Added to Portfolio' : 'Not in the portfolio'"
            v-model="symbol.checkbox"
            :color="colors"
          />
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">since {{ symbol.data.labels[0] }}</span>
          </template>
        </material-chart-card>
      </v-flex>

      <v-container class="hidden-sm-and-down">
        <v-layout>
          <v-flex>
            <v-layout justify-center>
              <h2>Calculate portfolio:</h2>
            </v-layout>
            <v-layout justify-center>
              <v-btn
                :color="colors"
                @click="calcReturns">Returns
              </v-btn>
            </v-layout>
          </v-flex>
        </v-layout>
      </v-container>

      <v-container
        fluid
        class="hidden-sm-and-down"
      >
        <v-layout row>
          <v-flex>
            <v-layout justify-center>
              <h2>Forecast {{ forecastDays }} days of {{ symbolToProphet }} with {{ changepointPriorScale }} prior scale</h2>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout >
                  <v-select
                    v-model="symbolToProphet"
                    :items="itemsCoins"
                    :color="colors"
                    outline
                    label="Select symbol"
                    return-object
                    single-line
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout>
                  <v-slider
                    v-model="forecastDays"
                    :color="colors"
                    :max="60"
                    :min="1"
                    label="Forecast days"
                    thumb-label="always"
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout >
                  <v-slider
                    v-model="changepointPriorScale"
                    :color="colors"
                    :max="1"
                    :min="0.01"
                    step="0.02"
                    label="Changepoint to consider a trend"
                    thumb-label="always"
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout row>
              <v-flex>
                <v-layout justify-center>
                  <v-btn
                    :color="colors"
                    @click.stop="btn">Plot
                  </v-btn>
                </v-layout>
              </v-flex>
            </v-layout>
          </v-flex>
        </v-layout>
      </v-container>
      <!-- ##### section 2 -->
      <!-- <v-flex
        sm6
        xs12
        md6
        lg3
      >
        <material-stats-card
          color="green"
          icon="mdi-note-outline"
          title="Sharpe ratio"
          value="0.09"
        />
      </v-flex>
      <v-flex
        sm6
        xs12
        md6
        lg3
      >
        <material-stats-card
          color="orange"
          icon="mdi-alpha"
          title="Alpha"
          value="1.00658"
        />
      </v-flex>
      <v-flex
        sm6
        xs12
        md6
        lg3
      >
        <material-stats-card
          color="red"
          icon="mdi-beta"
          title="Beta"
          value="1.5"
        />
      </v-flex>
      <v-flex
        sm6
        xs12
        md6
        lg3
      >
        <material-stats-card
          color="info"
          icon="mdi-asterisk"
          title="Risk"
          value="15%"
        />
      </v-flex> -->
      <!-- ###### section 3 -->

      <v-container
        fluid
        class="hidden-sm-and-down"
      >
        <v-layout row>
          <v-flex>
            <v-layout justify-center>
              <h2>Show {{ symbolToShowIndicators }} data to feed the trading bot</h2>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout >
                  <v-select
                    v-model="symbolToShowIndicators"
                    :items="itemsCoins"
                    :color="colors"
                    outline
                    label="Select symbol"
                    return-object
                    single-line
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout >
                  <v-select
                    v-model="modeToShowIndicators"
                    :items="['day', 'hour']"
                    :color="colors"
                    outline
                    label="Select mode"
                    return-object
                    single-line
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout justify-center>
              <v-flex
                xs12
                md6
              >
                <v-layout >
                  <v-slider
                    v-model="daysToShowIndicators"
                    :color="colors"
                    :max="2000"
                    :min="24"
                    :label="modeToShowIndicators + 's'"
                    thumb-label="always"
                  />
                </v-layout>
              </v-flex>
            </v-layout>
            <v-layout row>
              <v-flex>
                <v-layout justify-center>
                  <v-btn
                    :color="colors"
                    @click.stop="showIndicators">Show
                  </v-btn>
                </v-layout>
              </v-flex>
            </v-layout>
          </v-flex>
        </v-layout>
      </v-container>

      <v-container class="hidden-md-and-up">
        <h3 class="text-xs-center">Portfolio functions only available on desktop</h3>
      </v-container>
    </v-layout>
    <v-snackbar
      v-model="this.$store.state.snackbar"
      top
      color="red"
      dark
    >
      <v-icon
        color="white"
        class="mr-3"
      >
        mdi-bell-plus
      </v-icon>
      <div>{{ this.$store.state.snackbarMsg }}</div>
      <v-icon
        size="16"
        @click="snack()"
      >
        mdi-close-circle
      </v-icon>
    </v-snackbar>
  </v-container>
</template>

<script>
// https://github.com/Bud-Fox/client
// https://github.com/Bud-Fox/API

export default {
  data () {
    return {
      forecastDays: 15,
      modeToShowIndicators: 'day',
      daysToShowIndicators: 60,
      changepointPriorScale: 0.49,
      symbolToProphet: 'ETH',
      symbolToShowIndicators: 'ETH',
      ChartsOptions: {
        axisX: {
          showLabel: false,
          showGrid: false
        },
        lineSmooth: true,
        showPoint: false,
        showArea: true,
        chartPadding: {
          top: 25,
          right: 0,
          bottom: 0,
          left: 15
        }
      },
    }
  },
  computed: {
    loading () {
      return this.$store.getters.loading
    },
    symbolData () {
      return this.$store.getters.symbolData
    },
    itemsCoins () {
      var symbolList = []
      this.symbolData.map(function (item) {
        symbolList.push(item.botFood.pair)
      })
      return symbolList
    },
    colors () {
      return this.$store.state.app.color
    }
  },
  methods: {
    snack () {
      this.$store.state.snackbar = false
    },
    btn () {
      this.$store.commit('sendProphetReq', {
        forecast: this.forecastDays,
        symbol: this.symbolToProphet,
        changepoint: this.changepointPriorScale
      })
    },
    showIndicators () {
      this.$store.commit('sendIndicatorsReq', {
        symbol: this.symbolToShowIndicators,
        mode: this.modeToShowIndicators,
        limit: this.daysToShowIndicators
      })
    },
    calcReturns () {
      this.$store.dispatch('sendPortfolioRetunsReq')
    }
  }
}
</script>
