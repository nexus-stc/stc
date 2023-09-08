<template lang="pug">
div
  loading-spinner(v-if="references === null")
  div(v-else)
    div(v-for="(reference, i) of references")
      document-snippet.small(
        :document="JSON.parse(reference.document)",
        v-bind:key="reference.position",
        :with_abstract="false",
        :with_cover="false",
        :with_tags="false",
      )
      hr(v-if="i !== references.length - 1")
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue'

import LoadingSpinner from './LoadingSpinner.vue'
import DocumentSnippet from "@/components/DocumentSnippet.vue";

export default defineComponent({
  name: 'ReferencesList',
  components: {DocumentSnippet, LoadingSpinner },
  props: {
    references: {
      type: null as PropType<Array<{ document: any, position: number }>> | null
    }
  }
})
</script>
