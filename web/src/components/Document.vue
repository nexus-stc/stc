<template lang="pug">
div
  h3(v-html="document.title")
  .mt-1
    div(v-html="coordinates")
  .text-secondary
      span(v-html="extras")
  img.mt-3.img-thumbnail(v-if="!is_default_cover" width="160" :src="cover")
  .mt-3
    tags-list(:tags="document.tags")
  div(v-if="document.abstract")
    hr
    div(v-html="document.abstract")
  .text-end.mt-4
    document-buttons(:files="files" :query="id_query()")
  div(v-if="referenced_bys.length > 0 || is_references_loading")
    b Referenced by
    .card.mt-3
      .card-body
        div
          div(v-if="referenced_bys.length > 0")
            references-list(:references="referenced_bys")
            .d-grid(v-if="has_next")
              hr
              button.btn.btn-sm.btn-secondary(v-if="!is_references_loading" v-on:click="limit += 5; find_references()") {{ get_label('load_more') }}...
              button.btn.btn-sm.btn-secondary(v-else) {{ get_label('loading') + '...' }}
          loading-spinner(v-else-if="is_references_loading && referenced_bys.length === 0").mt-3.mb-3
          span(v-else) No references have been found
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import BaseDocument from "@/components/BaseDocument.vue";
import DocumentButtons from "@/components/DocumentButtons.vue";
import TagsList from "@/components/TagsList.vue";
import ReferencesList from "@/components/ReferencesList.vue";

export default defineComponent({
  name: 'Document',
  extends: BaseDocument,
  components: {
    ConnectivityIssuesView,
    DocumentButtons,
    LoadingSpinner,
    ReferencesList,
    TagsList,
  },
  data () {
    return {
      is_references_loading: false,
      referenced_bys: [],
      has_next: false,
      references_limit: 5
    }
  },
  async created () {
    console.log(this.document)
    this.find_references()
  },
  methods: {
    async find_references () {
      const dois = this.get_attr("dois")
      if (!dois || dois.length == 0) {
        return
      }
      try {
        this.is_references_loading = true
        const response = await this.search_service.search({
          index_alias: 'nexus_science',
          query: {
            query: {
              term: {
                field: 'rd',
                value: dois[0]
              }
            }
          },
          collectors: [
            {
              collector: {
                top_docs: {
                  limit: this.references_limit
                }
              }
            }
          ],
        })
        this.referenced_bys =
          response[0].collector_output.documents.scored_documents
      } finally {
        this.is_references_loading = false
      }
    }
  }
})
</script>
