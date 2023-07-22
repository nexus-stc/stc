<template lang="pug">
h5(v-html="document.title")
.small.mt-1
  .small(v-html="coordinates")
  .small.text-secondary
    span(v-html="extras")
  .clearfix
    .mt-2.text-secondary.float-start
      tags-list(:tags="document.tags")
.text-end.mt-4
  document-buttons(:external_links="external_links" :index_name="index_alias" :query="id_query()")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from 'vue'

import BaseNexusMedia from '../base/NexusMedia.vue'
import DocumentButtons from '../DocumentButtons.vue'

export default defineComponent({
  name: 'NexusMediaDocument',
  components: { DocumentButtons },
  extends: BaseNexusMedia
})
</script>
