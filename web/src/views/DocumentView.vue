<template lang="pug">
div(v-if="is_loading" style="margin-top: 140px")
  loading-spinner(:label="get_label('loading_document') + '...'")
div(v-else-if="is_loading_failed")
  connectivity-issues-view
div(v-else-if="scored_document").col-lg-9
  nexus-free-document(v-if='$route.params.index_alias === "nexus_free"', :scored_document="scored_document")
  nexus-media-document(v-if='$route.params.index_alias === "nexus_media"', :scored_document="scored_document")
  nexus-science-document(v-if='$route.params.index_alias === "nexus_science"', :scored_document="scored_document")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import NexusFreeDocument from "@/components/document/NexusFree.vue";
import NexusMediaDocument from "@/components/document/NexusMedia.vue";
import NexusScienceDocument from "@/components/document/NexusScience.vue";

export default defineComponent({
  name: "DocumentView",
  components: {
    ConnectivityIssuesView,
    LoadingSpinner,
    NexusFreeDocument,
    NexusMediaDocument,
    NexusScienceDocument,
  },
  props: {
    index_name: String,
    id: String,
  },
  data() {
    return {
      scored_document: undefined,
      is_loading: false,
      is_loading_failed: false,
    };
  },
  async created() {
    await this.submit();
  },
  methods: {
    async submit() {
      try {
        this.is_loading = true;
        let collector_outputs = await this.search_service.custom_search(this.id, {
          page: 1,
          page_size: 1,
          index_name: this.index_name,
        });
        this.scored_document =
          collector_outputs[0].collector_output.documents.scored_documents[0];
      } catch (e) {
        this.is_loading_failed = true;
      } finally {
        this.is_loading = false;
      }
    },
  },
  watch: {
    $route() {
      this.submit();
    },
  },
});
</script>
