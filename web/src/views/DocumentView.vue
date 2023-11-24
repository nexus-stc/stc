<template lang="pug">
.container
  loading-spinner(v-if="is_loading" style="margin-top: 140px" :label="get_label('loading_document') + '...'")
  connectivity-issues-view(v-else-if="is_loading_failed")
  div(v-else-if="not_found") Not found
  document(v-else-if="document" :document="document")
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import Document from "@/components/Document.vue";
import DocumentButtons from "@/components/DocumentButtons.vue";
import TagsList from "@/components/TagsList.vue";
import ReferencesList from "@/components/ReferencesList.vue";

export default defineComponent({
  name: 'DocumentView',
  components: {
    ConnectivityIssuesView,
    DocumentButtons,
    LoadingSpinner,
    ReferencesList,
    TagsList,
    Document
  },
  props: {
    id: {
      type: String,
      required: true
    }
  },
  data () {
    return {
      document: undefined,
      is_loading: false,
      is_loading_failed: false,
      not_found: false,
    }
  },
  watch: {
    $route () {
      void this.submit()
    }
  },
  async created () {
    await this.submit()
  },
  methods: {
    async submit () {
      try {
        this.is_loading = true
        const collector_outputs = await this.search_service.search(this.id, {
          page: 1,
          page_size: 1,
          index_name: this.index_name
        })
        const scored_documents = collector_outputs[0].collector_output.documents.scored_documents
        if (scored_documents.length === 0) {
          this.not_found = true;
          return;
        }
        this.not_found = false;
        this.document = JSON.parse(scored_documents[0].document)
        document.title = `${this.document.title} - STC`
      } catch (e) {
        this.is_loading_failed = true
      } finally {
        this.is_loading = false
      }
    }
  }
})
</script>
