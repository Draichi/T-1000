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
          :color="colors"
          :data="episodeRewardMax"
          :options="ChartsOptions"
          type="Line"
        >
          <h4 class="title font-weight-light">Episode Max Reward (BTC)</h4>
          <p class="category d-inline-flex font-weight-light">
            <!-- <v-icon
              color="green"
              small
            >
              mdi-account-check
            </v-icon> -->
            <span class="green--text">&nbsp;{{ episodeRewardMax.labels.slice(-1)[0] }}</span>&nbsp; episodes total

          </p>
          <template slot="actions">
            <v-icon
              class="mr-2"
              small
            >
              mdi-clock-outline
            </v-icon>
            <span class="caption grey--text font-weight-light">since 123</span>
          </template>
        </material-chart-card>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script>

export default {
  data () {
    return {
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
      }
    }
  },
  computed: {
    loading () {
      return this.$store.getters.loading
    },
    episodeRewardMax () {
      return this.$store.getters.episodeRewardMax
    },
    colors () {
      return this.$store.state.app.color
    }
  }
}
</script>
