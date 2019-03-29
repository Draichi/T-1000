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
        md12
        sm12
        lg4
      >
        <material-chart-card
          :data="ETHBTCData"
          :options="ChartsOptions"
          color="purple"
          type="Line"
        >
          <h4 class="title font-weight-light">ETHBTCData</h4>
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">ETHBTCData</span>
          </template>
        </material-chart-card>
      </v-flex>
      <div>
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
        lg6
      >
        <material-card
          class="card-tabs"
          color="green">
          <v-flex
            slot="header"
          >
            <v-tabs
              v-model="tabs"
              color="transparent"
              slider-color="white"
            >
              <span
                class="subheading font-weight-light mr-3"
                style="align-self: center"
              >Tasks:</span>
              <v-tab class="mr-3">
                <v-icon class="mr-2">mdi-bug</v-icon>
                Bugs
              </v-tab>
              <v-tab class="mr-3">
                <v-icon class="mr-2">mdi-code-tags</v-icon>
                Website
              </v-tab>
              <v-tab>
                <v-icon class="mr-2">mdi-cloud</v-icon>
                Server
              </v-tab>
            </v-tabs>
          </v-flex>

          <v-tabs-items v-model="tabs">
            <v-tab-item
              v-for="n in 3"
              :key="n"
            >
              <v-list three-line>
                <v-list-tile @click="complete(0)">
                  <v-list-tile-action>
                    <v-checkbox
                      :value="list[0]"
                      color="green"
                    />
                  </v-list-tile-action>
                  <v-list-tile-title>
                    Sign contract for "What are conference organized afraid of?"
                  </v-list-tile-title>
                  <div class="d-flex">
                    <v-tooltip
                      top
                      content-class="top">
                      <v-btn
                        slot="activator"
                        class="v-btn--simple"
                        color="success"
                        icon
                      >
                        <v-icon color="primary">mdi-pencil</v-icon>
                      </v-btn>
                      <span>Edit</span>
                    </v-tooltip>
                    <v-tooltip
                      top
                      content-class="top">
                      <v-btn
                        slot="activator"
                        class="v-btn--simple"
                        color="danger"
                        icon
                      >
                        <v-icon color="error">mdi-close</v-icon>
                      </v-btn>
                      <span>Close</span>
                    </v-tooltip>

                  </div>
                </v-list-tile>
                <v-divider/>
              </v-list>
            </v-tab-item>
          </v-tabs-items>
        </material-card>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script>
// https://github.com/Bud-Fox/client
// https://github.com/Bud-Fox/API

// TODO:

// - juntar tudo o que foi trabalhado
// (wieths , efficiente frontier, prophet, hype)
// no dash e calcular o portfolio sharpe ratio, alpha, beta, risk...

// Pra isso vai ser necessario tranformar o plot_portfolio.py em um server

export default {
  data () {
    return {
      forecastDays: 2,
      changepointPriorScale: null,
      changepointList: [0.01, 0.02, 0.03],
      ChartsOptions: {
        axisX: {
          showLabel: false,
          showGrid: true
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
      tabs: 0,
      list: {
        0: true,
        1: false,
        2: false
      }
    }
  },
  computed: {
    loading () {
      return this.$store.getters.loading
    },
    ETHBTCData () {
      return this.$store.getters.ETHBTCData
    }
  },
  methods: {
    complete (index) {
      this.list[index] = !this.list[index]
    },
    btn () {
      this.$store.dispatch('sendProphetReq')
    }
  }
}
</script>
