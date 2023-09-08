<template lang="pug">
div(v-for="scored_document in scored_documents" v-bind:key="scored_document.position")
  .card.mb-3
    .card-body
      document-snippet(
        :document="JSON.parse(scored_document.document)"
        :snippets="scored_document.snippets",
        :with_abstract="true"
        :with_cover="true"
        :with_large_caption="true"
      )
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import DocumentSnippet from '@/components/DocumentSnippet.vue'

export default defineComponent({
  name: 'SearchList',
  components: { DocumentSnippet },
  props: {
    scored_documents: {
      type: Array,
      required: true
    }
  }
})
</script>

<style scoped lang="scss">
li {
  padding-bottom: 15px;
  padding-left: 0;
  &:after {
    content: none;
  }
}
</style>
