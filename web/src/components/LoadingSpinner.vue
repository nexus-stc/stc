<template lang="pug">
div(v-if="is_launched")
  .d-flex.justify-content-center
    .spinner-border(role="status")
  .d-flex.justify-content-center.m-5(v-if="label")
    div {{ label }}
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'LoadingSpinner',
  props: {
    label: {
      default: '',
      type: String
    }
  },
  data () {
    return {
      is_launched: false
    }
  },
  created () {
    setInterval(() => {
      this.is_launched = true
    }, 300)
  }
})
</script>
