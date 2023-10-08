<template lang="pug">
.container
  h2 {{ get_label('how_to_search') }}
  span(v-html="get_label('help')")
</template>
<script lang="ts">
import { defineComponent } from 'vue'
import {get_label} from "@/translations";
export default defineComponent({
  name: 'HowToSearchView',
  created () {
    document.title = `${get_label('how_to_search')} - Help - STC`
  }
})
</script>
