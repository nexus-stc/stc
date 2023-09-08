<template lang="pug">
div
  span(v-for="(tag, index) in tags")
    span.ms-1.me-1(v-if="index > 0") -
    router-link.text-decoration-none(:to="'/?q=tags:\"' + tag + '\"'") {{ tag }}
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue'

export default defineComponent({
  name: 'TagsList',
  props: {
    tags: {
      type: Array as PropType<string[]>
    }
  }
})
</script>
