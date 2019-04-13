<template>
  <v-navigation-drawer
    id="app-drawer"
    v-model="inputValue"
    app
    dark
    floating
    persistent
    mobile-break-point="991"
    width="260"
  >
    <v-img
      :src="image"
      height="100%"
    >
      <v-layout
        class="fill-height"
        tag="v-list"
        column
      >
        <v-list-tile>
        <!-- <v-list-tile avatar>
          <v-list-tile-avatar color="white">
            <v-img :src="logo"/>
          </v-list-tile-avatar> -->
          <v-list-tile-title class="title">Crypto Prediction</v-list-tile-title>
        </v-list-tile>
        <v-divider/>
        <v-list-tile
          v-if="responsive"
        >
          <v-text-field
            class="purple-input search-input"
            label="Search..."
            color="purple"
          />
        </v-list-tile>
        <v-list-tile
          v-for="(link, i) in links"
          :key="i"
          :to="link.to"
          :active-class="color"
          avatar
          class="v-list-item"
        >
          <v-list-tile-action>
            <v-icon>{{ link.icon }}</v-icon>
          </v-list-tile-action>
          <v-list-tile-title
            v-text="link.text"
          />
        </v-list-tile>
        <a href="https://github.com/Draichi/cryptocurrency_prediction" target="_blank" rel="noopener noreferrer">
          <v-list-tile
            :active-class="color"
            avatar
            class="v-list-item"
          >
            <v-list-tile-action>
              <v-icon>mdi-github-circle</v-icon>
            </v-list-tile-action>
            <v-list-tile-title><span class="white--text">Github</span></v-list-tile-title>
          </v-list-tile>
        </a>
        <a href="https://bud-fox.github.io/live/" target="_blank" rel="noopener noreferrer">
          <v-list-tile
            :active-class="color"
            avatar
            class="v-list-item"
          >
            <v-list-tile-action>
              <v-icon>mdi-finance</v-icon>
            </v-list-tile-action>
            <v-list-tile-title><span class="white--text">Budfox</span></v-list-tile-title>
          </v-list-tile>
        </a>
        <a href="https://draichi.github.io/draichiboard/" target="_blank" rel="noopener noreferrer">
          <v-list-tile
            :active-class="color"
            avatar
            class="v-list-item"
          >
            <v-list-tile-action>
              <v-icon>mdi-chart-areaspline</v-icon>
            </v-list-tile-action>
            <v-list-tile-title><span class="white--text">Draichiboard</span></v-list-tile-title>
          </v-list-tile>
        </a>
      </v-layout>
    </v-img>
  </v-navigation-drawer>
</template>

<script>
// Utilities
import {
  mapMutations,
  mapState
} from 'vuex'

export default {
  data: () => ({
    // logo: './img/logo.png',
    links: [
      {
        to: '/dashboard',
        icon: 'mdi-view-dashboard',
        text: 'Dashboard'
      },
      {
        to: '/maps',
        icon: 'mdi-chart-scatterplot-hexbin',
        text: 'Algotrading Bot'
      },
      {
        to: '/notifications',
        icon: 'mdi-bell',
        text: 'Notifications'
      },
      {
        to: '/user-profile',
        icon: 'mdi-account',
        text: 'About the dev'
      }
    ],
    responsive: false
  }),
  computed: {
    ...mapState('app', ['image', 'color']),
    inputValue: {
      get () {
        return this.$store.state.app.drawer
      },
      set (val) {
        this.setDrawer(val)
      }
    },
    items () {
      return this.$t('Layout.View.items')
    }
  },
  mounted () {
    this.onResponsiveInverted()
    window.addEventListener('resize', this.onResponsiveInverted)
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.onResponsiveInverted)
  },
  methods: {
    ...mapMutations('app', ['setDrawer', 'toggleDrawer']),
    onResponsiveInverted () {
      if (window.innerWidth < 991) {
        this.responsive = true
      } else {
        this.responsive = false
      }
    }
  }
}
</script>

<style lang="scss">
  #app-drawer {
    .v-list__tile {
      border-radius: 4px;

      &--buy {
        margin-top: auto;
        margin-bottom: 17px;
      }
    }

    .v-image__image--contain {
      top: 9px;
      height: 60%;
    }

    .search-input {
      margin-bottom: 30px !important;
      padding-left: 15px;
      padding-right: 15px;
    }
  }
</style>
