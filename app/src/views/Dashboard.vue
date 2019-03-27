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
          :data="dailySalesChartGraph.data"
          color="info"
          type="Line"
        >
          <h4 class="title font-weight-light">Bitcoin</h4>
          <!-- <p class="category d-inline-flex font-weight-light">
            <v-icon
              color="green"
              small
            >
              mdi-arrow-up
            </v-icon>
            <span class="green--text">{{ change }}%</span>&nbsp;
            increase in today's sales
          </p> -->
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">hourly</span>
          </template>
        </material-chart-card>
      </v-flex>
      <v-flex
        md12
        sm12
        lg4
      >
        <material-chart-card
          :data="emailsSubscriptionChartGraph.data"
          :responsive-options="emailsSubscriptionChartGraph.responsiveOptions"
          color="red"
          type="Bar"
        >
          <h4 class="title font-weight-light">Ethereum</h4>
          <!-- <p class="category d-inline-flex font-weight-light">Last Campaign Performance</p> -->
          <template slot="actions">
            <!-- <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon> -->
            <span class="caption grey--text font-weight-light">hourly</span>
          </template>
        </material-chart-card>
      </v-flex>
      <v-flex
        md12
        sm12
        lg4
      >
        <material-chart-card
          :data="dataCompletedTasksChartGraph.data"
          color="green"
          type="Line"
        >
          <h3 class="title font-weight-light">Bitcoin vs Ethereum</h3>
          <!-- <p class="category d-inline-flex font-weight-light">Last Last Campaign Performance</p> -->
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">hourly</span>
          </template>
        </material-chart-card>
      </v-flex>
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
// import axios from 'axios'

export default {
  data () {
    return {
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
    dataCompletedTasksChartGraph () {
      return this.$store.getters.dataCompletedTasksChart
    },
    dailySalesChartGraph () {
      return this.$store.getters.dailySalesChart
    },
    emailsSubscriptionChartGraph () {
      return this.$store.getters.emailsSubscriptionChartGraph
    }
  },
  methods: {
    complete (index) {
      this.list[index] = !this.list[index]
    }
  }
}
</script>
