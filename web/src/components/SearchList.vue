<template lang="pug">
div(v-for="scored_document in scored_documents" v-bind:key="scored_document.position").small
  .card.mb-3
    .card-body
      document-snippet(:scored_document="scored_document" :with_abstract="true")
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue";
import DocumentSnippet from "@/components/DocumentSnippet.vue";

export default defineComponent({
  name: "SearchList",
  components: { DocumentSnippet },
  props: {
    scored_documents: {
      type: Array as PropType<
        {
          document: {
            title: string;
            cid: string;
          };
        }[]
      >,
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
