<template lang="pug">
h6 {{ get_label("what_to_read") }}
  a.ms-3.text-decoration-none(v-if="!is_loading" @click.stop.prevent="roll") 🎲
div(v-if="is_loading" style="margin-top: 140px")
  loading-spinner(:label="get_label('loading') + '...'")
connectivity-issues-view(v-else-if="is_loading_failed")
.card.mb-3(v-else)
  .card-body
    div(v-for="(scored_document, i) of scored_documents" v-bind:key="scored_document.position").small
      document-snippet(:scored_document="scored_document" :with_abstract="false" :with_tags="false" :with_extras="false")
      hr(v-if="i !== scored_documents.length - 1")
</template>

<script lang="ts">
import { defineComponent } from "vue";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import DocumentSnippet from "@/components/DocumentSnippet.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import {get_label} from "../translations";

export default defineComponent({
  name: "ItemsShowcase",
  components: { ConnectivityIssuesView, DocumentSnippet, LoadingSpinner },
  data() {
    return {
      is_loading: false,
      is_loading_failed: false,
      scored_documents: [],
    }
  },
  async created() {
    try {
        this.is_loading = true;
        const items = [
            "cid:bafkr4idc3rvn6wvd4fubfvlif3q2bz4b65yihxipozwlz2vazutetxcnv4^199",
            "cid:bafykbzaceabhqlewtuuab2ajvwwuygqp4nybo73bqdx3e5udoeqiw5ft7pok4",
            "cid:bafykbzaceboi2utkjiavwilazo3plwaldgjc2j65owxe6nbxpe373vlo2mos6",
            "cid:bafykbzacebczpon2rotpza2vugi4t3g325cepwnv4zxjk3qwt4lr2zf2kbdsk^0.002",
            "cid:bafyb4igypipnbm7lbfjmswwv33cqihv6mlq6kqzpy2qhlvqmlcqpmewlwq^200",
            "cid:bafyb4ieuzpjaavuqgxocpel3bj5vyql7xf3wzkhckqd34rzm2dx6gwcn6e^0.001",
            "cid:bafykbzaceaxd43fphhrftravlfevlphirolsvnzzbhsl44v7l7mdb43n4x654",
            "cid:bafyb4ichi55vmzosyaoafrpb3aij7r32tguvu62a4jd3vf27w2lxqnsr6i"
        ]
        let collector_outputs = await this.search_service.custom_search(items.join(" "), {
          page: 1,
          page_size: 20,
        });
        this.scored_documents = collector_outputs[0].collector_output.documents.scored_documents;
      } catch (e) {
        this.is_loading_failed = true;
      } finally {
        this.is_loading = false;
      }
  },
  methods: {
    get_label,
    async roll() {
      try {
        this.is_loading = true;
        let collector_outputs = await this.search_service.random_search({
          page: 1,
          page_size: 5,
          index_name: "nexus_science",
        });
        this.scored_documents = collector_outputs[0].collector_output.documents.scored_documents;
      } catch (e) {
        this.is_loading_failed = true;
      } finally {
        this.is_loading = false;
      }
    }
  }
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
