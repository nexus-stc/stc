<template lang="pug">
.container
  h3 Doomsday Guide
  p In the event of an extinction-level occurrence (such as a nuclear war, global pandemic, or impact event), this space will provide links to a rescue kit and literature on the subject of civilization restoration.
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'DoomsdayView',
  created () {
    document.title = 'Doomsday Guide - Help - STC'
  }
})
</script>
