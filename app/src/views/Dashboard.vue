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
        v-for="(symbol, indx) in symbolDataFiltered"
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
            <v-layout row>
              <v-flex>
                <v-layout justify-center>
                  <v-btn
                    :color="colors"
                    @click="showIndicators">Show
                  </v-btn>
                </v-layout>
              </v-flex>
            </v-layout>
          </v-flex>
        </v-layout>
      </v-container>

      <v-flex
        md12
      >
        <material-card
          color="green"
          title="Top Market Cap Coins"
          text="..."
        >
          <v-data-table
            :headers="headers"
            :items="topCoinsTable"
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
              <td>{{ item.CoinInfo.FullName }}</td>
              <td>{{ item.CoinInfo.Name }}</td>
              <td>{{ item.CoinInfo.Algorithm }}</td>
              <td>{{ item.CoinInfo.ProofType }}</td>
            </template>
          </v-data-table>
        </material-card>
      </v-flex>
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
          text: 'Algorithm',
          value: 'Algorithm'
        },
        {
          sortable: false,
          text: 'ProofType',
          value: 'ProofType'
        }
      ]
    }
  },
  computed: {
    loading () {
      return this.$store.getters.loading
    },
    symbolData () {
      return this.$store.getters.symbolData
    },
    topCoinsTable () {
      return this.$store.getters.topCoinsTable
    },
    fisrtIndex () {
      return  Object.keys(item.info.DISPLAY)[0]
    },
    symbolDataFiltered () {
      var symbolDataList = []
      this.symbolData.map(function (item) {
        var firstIndex = Object.keys(item.info.DISPLAY)[0]
        var fromSymbol = item.info.RAW[firstIndex].FROMSYMBOL
        var toSymbol = item.info.RAW[firstIndex].TOSYMBOL
        if (fromSymbol != toSymbol) {
          symbolDataList.push(item)
        }
      })
      return symbolDataList
    },
    itemsCoins () {
      var symbolList = []
      this.symbolData.map(function (item) {
        symbolList.push(item.info.CoinInfo.Name)
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
        symbol: this.symbolToShowIndicators
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
