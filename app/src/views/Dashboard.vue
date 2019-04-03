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
      >
        <v-flex
          md12
          sm12
          lg4
        >
          <material-chart-card
            :data="symbol.data"
            :options="ChartsOptions"
            color="green"
            type="Line"
          >
            <h4 class="title font-weight-light">{{ symbol.coin }}/BTC</h4>
            <v-checkbox
              v-model="symbol.checkbox"
              color="green"
              :label="symbol.coin"
            />
            <p
              class="category d-inline-flex font-weight-light"
              v-if="symbol.checkbox"
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
              class="category d-inline-flex font-weight-light"
              v-else
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
              <span class="caption grey--text font-weight-light">from {{ symbol.data.labels[0] }} to {{ symbol.data.labels.slice(-1)[0] }}</span>
            </template>
          </material-chart-card>
        </v-flex>
      </v-flex>
      <!-- <v-flex
        md12
        sm12
        lg4
      >
        <material-chart-card
          :data="ETHBTCData"
          :options="ChartsOptions"
          :color="this.$store.state.app.color"
          type="Line"
        >
          <h4 class="title font-weight-light">Historical ETH</h4>
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">from {{ ETHBTCData.labels[0] }} to {{ ETHBTCData.labels.slice(-1)[0] }}</span>
          </template>
        </material-chart-card>
      </v-flex> -->
      <div>
        <v-btn
          color="info"
          @click="calcReturns">Calculate Portfolio Returns
        </v-btn>
        <v-btn
          color="info"
          @click="calcCorrelation">Calculate Portfolio Correlation
        </v-btn>
        <v-btn
          color="info"
          @click="calcEfficientFrontier">calcEfficientFrontier
        </v-btn>
        <v-flex>
          <v-slider
            v-model="forecastDays"
            :max="5"
            :min="1"
            label="Forecast days"
            thumb-label="always"
          />
        </v-flex>
        <v-select
          v-model="changepointPriorScale"
          :items="changepointList"
          outline
          label="Changepoint to consider a trend"
          return-object
          single-line
        />
        <v-btn
          color="info"
          @click="btn">Info
        </v-btn>
      </div>
      <!-- ##### section 2 -->
      <v-flex
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
      </v-flex>
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
    </v-layout>
    <v-layout v-else><h2>Loading</h2></v-layout>
  </v-container>
</template>

<script>
// https://github.com/Bud-Fox/client
// https://github.com/Bud-Fox/API

export default {
  data () {
    return {
      list: {
        0: true
      },
      forecastDays: 2,
      changepointPriorScale: null,
      changepointList: [0.01, 0.02, 0.03],
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
    }
  },
  methods: {
    complete (index) {
      this.list[index] = !this.list[index]
    },
    btn () {
      this.$store.dispatch('sendProphetReq')
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
