<template lang="pug">
div
  loading-spinner(v-if="references === null")
  div(v-else)
    div(v-for="(reference, i) of references")
      nexus-science-snippet(
        :scored_document="reference",
        v-bind:key="reference.position",
        :with_abstract="false",
        :with_large_caption="false",
        :with_tags="false",
      )
      hr(v-if="i !== references.length - 1")
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import LoadingSpinner from "./LoadingSpinner.vue";
import NexusScienceSnippet from "./snippet/NexusScience.vue";

export default defineComponent({
  name: "ReferencesList",
  components: { NexusScienceSnippet, LoadingSpinner },
  props: {
    references: {
      type: null as PropType<Array<{ document: any, position: number }>> | null,
    },
  },
});
</script>
