<template lang="pug">
div
  h5(v-html="document.title")
  .small.mt-1
    .small(v-html="coordinates")
    .small.text-secondary
      span(v-html="extras")
    div(v-if="document.abstract")
      hr
      div(v-html="document.abstract")
    .clearfix
      .mt-2.text-secondary.float-start
        tags-list(:tags="document.tags")
    .text-end.mt-4
      document-buttons(:external_links="external_links" :index_name="index_name" :query="id_query()")
  div Referenced by
  .card.mt-3.small
    .card-body
      div
        div(v-if="referenced_bys.length > 0")
          references-list.small(:references="referenced_bys")
          .d-grid(v-if="has_next")
            hr
            button.btn.btn-sm.btn-secondary(v-if="!is_references_loading" v-on:click="limit += 5; find_references()") {{ get_label('load_more') }}...
            button.btn.btn-sm.btn-secondary(v-else) {{ get_label('loading') + '...' }}
        loading-spinner(v-else-if="is_references_loading && referenced_bys.length === 0").mt-3.mb-3
        span(v-else) No references have been found
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import BaseNexusScience from '../base/NexusScience.vue'
import DocumentButtons from '../DocumentButtons.vue'
import LoadingSpinner from '../LoadingSpinner.vue'
import ReferencesList from '../ReferencesList.vue'

export default defineComponent({
  name: 'NexusScienceDocument',
  components: { LoadingSpinner, ReferencesList, DocumentButtons },
  extends: BaseNexusScience,
  data () {
    return {
      referenced_bys: [],
      is_references_loading: false,
      has_next: false,
      limit: 5
    }
  },
  created () {
    document.title = `${this.document.title} - STC`
    console.log(this.document)
    this.find_references()
  },
  methods: {
    async find_references () {
      try {
        this.is_references_loading = true
        const response = await this.search_service.search([
          {
            index_alias: 'nexus_science',
            query: {
              query: {
                term: {
                  field: 'rd',
                  value: this.document.doi
                }
              }
            },
            collectors: [
              {
                collector: {
                  top_docs: {
                    limit: this.limit
                  }
                }
              }
            ],
            is_fieldnorms_scoring_enabled: false
          }
        ])
        this.referenced_bys =
          response[0].collector_output.documents.scored_documents
        this.has_next = response[0].collector_output.documents.has_next
      } finally {
        this.is_references_loading = false
      }
    }
  }
})
</script>
