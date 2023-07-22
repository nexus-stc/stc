<template lang="pug">
.container
  h2 How to Search?
  span(v-html="get_label('help')")
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'HowToSearchView',
  created () {
    document.title = 'How to Search - Help - STC'
  }
})
</script>
