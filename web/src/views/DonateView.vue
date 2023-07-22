<template lang="pug">
.container
  h4 Donate
  p(v-html='get_label("donate")')
  .col-lg-6.small
    ul.nav.nav-tabs(id="currencies-tab" role="tablist")
      li.nav-item(role="presentation")
        button.nav-link.active(id="btc-tab" data-bs-toggle="tab" data-bs-target="#btc-tab-pane" type="button" role="tab" aria-controls="btc-tab-pane" aria-selected="true") BTC
      li.nav-item(role="presentation")
        button.nav-link(id="eth-tab" data-bs-toggle="tab" data-bs-target="#eth-tab-pane" type="button" role="tab" aria-controls="eth-tab-pane" aria-selected="false") ETH
      li.nav-item(role="presentation")
        button.nav-link(id="xmr-tab" data-bs-toggle="tab" data-bs-target="#xmr-tab-pane" type="button" role="tab" aria-controls="xmr-tab-pane" aria-selected="false") XMR

    .tab-content.mt-3(id="currencies-tab-content")
      .tab-pane.fade.show.active(id="btc-tab-pane" role="tabpanel" aria-labelledby="btc-tab")
        p
          code 357vJAFsYeCtLU36MYEgaDueg34rr5ajCy
        p
          img.favicon-inversion-filter.img-fluid(src="@/assets/btc.svg")
      .tab-pane.fade(id="eth-tab-pane" role="tabpanel" aria-labelledby="eth-tab")
        p
          code 0x199bECe965e4e1e2fE3065d3F551Ebe8520AC555
        p
          img.favicon-inversion-filter.img-fluid(src="@/assets/eth.svg")
      .tab-pane.fade(id="xmr-tab-pane" role="tabpanel" aria-labelledby="xmr-tab")
        p
          code 42HZx5Cg1uQ2CtCrq7QabP23BN7gBrGu6U6QumkMmR4bKS61gcoP8xyNzP5cJCbjac9yaWFhLsDmM3adMWyBKBXn1d9WiUb
        p
          img.favicon-inversion-filter.img-fluid(src="@/assets/xmr.svg")
</template>
<script lang="ts">
import { defineComponent } from 'vue'

import { get_label } from '../translations'
export default defineComponent({
  name: 'DonateView',
  created () {
    document.title = 'Donate - Help - STC'
  },
  methods: { get_label }
})
</script>
