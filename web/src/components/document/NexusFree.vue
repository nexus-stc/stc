<template lang="pug">
h5(v-html="document.title")
.small.mt-1
  .small(v-html="coordinates")
  .small.text-secondary
    span(v-html="extras")
img.mt-3.img-thumbnail(v-if="cover" width="160" :src="cover")
.small(v-if="document.abstract")
  hr
  div(v-html="document.abstract")
.clearfix.small
  .mt-2.text-secondary.float-start
    tags-list(:tags="document.tags")
.text-end.mt-4
  document-buttons(:external_links="external_links" :index_name="index_name" :query="id_query()" :cid="document.primary_link")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import BaseNexusFree from "../base/NexusFree.vue";
import DocumentButtons from "../DocumentButtons.vue";

export default defineComponent({
  name: "NexusFreeDocument",
  extends: BaseNexusFree,
  components: { DocumentButtons },
  async created() {
    document.title = `${this.document.title} - STC`;
  },
});
</script>
