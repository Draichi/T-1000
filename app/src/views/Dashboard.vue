<template>
  <v-container
    fill-height
    fluid
    grid-list-xl
  >
    <v-layout
      v-if="!loading"
      wrap
    >
      <v-flex
        v-for="symbol in symbolData"
        :key="symbol.coin"
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
          <h4 class="title font-weight-light">{{ symbol.coin }}/BTC</h4>
          <v-checkbox
            :label="`Last price: ${symbol.data.series[0].slice(-1)[0]} BTC`"
            v-model="symbol.checkbox"
            :color="colors"
          />
          <p
            v-if="symbol.checkbox"
            class="category d-inline-flex font-weight-light"
          >
            <v-icon
              color="green"
              small
            >
              mdi-account-check
            </v-icon>
            <span class="green--text">&nbsp;Added to portfolio</span>

          </p>
          <p
            v-else
            class="category d-inline-flex font-weight-light"
          >
            <v-icon
              color="red"
              small
            >
              mdi-account-plus
            </v-icon>
            <span class="red--text">&nbsp;Not in portfolio</span>
          </p>
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
            <v-layout justify-center>
              <v-btn
                :color="colors"
                @click="calcCorrelation">Correlation
              </v-btn>
            </v-layout>
            <v-layout justify-center>
              <v-btn
                :color="colors"
                @click="calcEfficientFrontier">Efficient Frontier
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
                    @click="btn">Plot
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
      <v-flex
        md12
      >
        <material-card
          color="green"
          title="Top 24h Volume"
          text="Volume in BTC"
        >
          <v-data-table
            :headers="headers"
            :items="topVolCoins"
            hide-actions
          >
            <template
              slot="headerCell"
              slot-scope="{ header }"
            >
              <span
                class="subheading font-weight-light text-success text--darken-3"
                v-text="header.text"
              />
            </template>
            <template
              slot="items"
              slot-scope="{ item }"
            >
              <td>{{ item.NAME }}</td>
              <td>{{ item.SYMBOL }}</td>
              <td>{{ item.VOLUME24HOURTO }}</td>
            </template>
          </v-data-table>
        </material-card>
      </v-flex>
      <v-container class="hidden-md-and-up">
        <h3 class="text-xs-center">Portfolio functions only available on desktop</h3>
      </v-container>
    </v-layout>
    <v-snackbar
      top
      color="red"
      v-model="this.$store.state.snackbar"
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
      changepointPriorScale: 0.49,
      symbolToProphet: 'ETH',
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
      headers: [
        {
          sortable: false,
          text: 'Name',
          value: 'NAME'
        },
        {
          sortable: false,
          text: 'Symbol',
          value: 'SYMBOL'
        },
        {
          sortable: false,
          text: 'Volume',
          value: 'VOLUME24HOURTO'
        }
      ]
    }
  },
  computed: {
    loading () {
      return this.$store.getters.loading
    },
    topVolCoins () {
      return this.$store.getters.topVolCoins
    },
    symbolData () {
      return this.$store.getters.symbolData
    },
    itemsCoins () {
      var symbolList = []
      this.topVolCoins.map(function (item) {
        symbolList.push(item.SYMBOL)
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
    calcReturns () {
      this.$store.dispatch('sendPortfolioRetunsReq')
    },
    calcCorrelation () {
      this.$store.dispatch('sendPortfolioCorrelationReq')
    },
    calcEfficientFrontier () {
      this.$store.dispatch('sendPortfolioEfficientFrontierReq')
    }
  }
}
</script>
