<template lang="pug">
div
  nexus-free-snippet(v-if='scored_document.index_alias === "nexus_free"' :scored_document = "scored_document" :with_abstract="with_abstract" :with_tags="with_tags" :with_extras="with_extras")
  nexus-media-snippet(v-if='scored_document.index_alias === "nexus_media"' :scored_document = "scored_document" :with_abstract="with_abstract" :with_tags="with_tags" :with_extras="with_extras")
  nexus-science-snippet(v-if='scored_document.index_alias === "nexus_science"' :scored_document = "scored_document" :with_abstract="with_abstract" :with_tags="with_tags" :with_extras="with_extras")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import NexusFreeSnippet from "./snippet/NexusFree.vue";
import NexusMediaSnippet from "./snippet/NexusMedia.vue";
import NexusScienceSnippet from "./snippet/NexusScience.vue";

export default defineComponent({
  name: "DocumentSnippet",
  components: { NexusFreeSnippet, NexusMediaSnippet, NexusScienceSnippet },
  props: {
    with_abstract: {
      type: Boolean,
      required: false,
      default: true,
    },
    with_extras: {
      type: Boolean,
      required: false,
      default: true,
    },
    with_tags: {
      type: Boolean,
      required: false,
      default: true,
    },
    scored_document: {
      type: Object,
      required: true,
    },
  },
});
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
