<template lang="pug">
a.text-decoration-none.h6(v-if="with_large_caption" v-html="title" :href="external_links[0].url")
a.text-decoration-none.fw-bold(v-else v-html="title" :href="external_links[0].url" style="color: inherit;")
div
  .small.mt-1(v-html="coordinates")
  .small.text-secondary(v-if="with_extras")
    span(v-html="extras")
  .small.clearfix(v-if="document.tags && with_tags")
    .mt-2.text-secondary.float-start
      tags-list(:tags="small_tags")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import BaseNexusMedia from "@/components/base/NexusMedia.vue";

export default defineComponent({
  name: "NexusMediaSnippet",
  extends: BaseNexusMedia,
  props: {
    with_abstract: {
      type: Boolean,
      default: true,
    },
    with_extras: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  data() {
    return {
      snippet_length: 340,
    };
  },
});
</script>
