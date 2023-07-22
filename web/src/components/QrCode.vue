<template lang="pug">
div.favicon-inversion-filter.text-center(id="qr-code")
</template>

<script lang="ts">
import QrCreator from 'qr-creator'
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'QrCode',
  props: {
    url: {
      default: '',
      type: String
    }
  },
  async mounted () {
    QrCreator.render(
      {
        text: this.url,
        radius: 0.5, // 0.0 to 0.5
        ecLevel: 'H', // L, M, Q, H
        fill: '#000000', // foreground color
        background: null, // color or null for transparent
        size: 280 // in pixels
      },
      document.querySelector('#qr-code')!
    )
  }
})
</script>
