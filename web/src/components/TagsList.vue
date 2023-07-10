<template lang="pug">
span(v-for="(tag, index) in tags")
  span.me-2.ms-2(v-if="index > 0") -
  router-link.link-secondary.text-decoration-none(:to="'/?q=tags:\"' + tag + '\"'") {{ tag }}
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";

export default defineComponent({
  name: "TagsList",
  props: {
    tags: {
      type: Array as PropType<Array<string>>,
    },
  },
});
</script>
