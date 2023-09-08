<template lang="pug">
.container.col-md-7.offset-md-2
  div(v-if="is_loading" style="margin-top: 140px")
    loading-spinner(:label="get_label('loading') + '...'")
  div(v-else-if="loading_failure_reason !== undefined")
    connectivity-issues-view(:reason="loading_failure_reason")
  div(v-else)
    .d-flex
      i.ms-3.me-auto {{ bookmarks.length }} {{ get_label('bookmarks') }}
      a.text-secondary(type="button" @click.stop.prevent="export_bookmarks") export
    div.mt-3.mb-3(v-if="!is_loading")
      search-list(:scored_documents='documents')
      nav(v-if="bookmarks.length > page_size")
        ul.pagination.justify-content-center
          li.page-item(v-if="page > 2" v-on:click="set_page(1);")
            a.page-link &lt;&lt;
          li.page-item(v-on:click="set_page(page - 1);")
            a.page-link &lt;
          li.page-item.disabled
            a.page-link {{ page }}
          li.page-item(v-if="bookmarks.length > page * page_size", v-on:click="set_page(page + 1);")
            a.page-link &gt;
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { RouterLink } from 'vue-router'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SearchList from '@/components/SearchList.vue'
import { user_db } from '@/database'

export default defineComponent({
  name: 'SearchView',
  components: {
    ConnectivityIssuesView,
    LoadingSpinner,
    RouterLink,
    SearchList
  },
  data () {
    return {
      page: 1,
      page_size: 5,
      is_loading: false,
      loading_failure_reason: undefined,
      bookmarks: [],
      documents: []
    }
  },
  async created () {
    try {
      document.title = 'Bookmarks - STC'
      this.is_loading = true
      this.bookmarks = await user_db.get_all_bookmarks()
      await this.submit()
    } catch (e) {
      console.error(e)
      this.loading_failure_reason = e
    } finally {
      this.is_loading = false
    }
  },
  methods: {
    async export_bookmarks () {
      const element = document.createElement('a')
      element.setAttribute(
        'href',
        'data:text/plain;charset=utf-8,' +
          encodeURIComponent(JSON.stringify(await user_db.get_all_bookmarks()))
      )
      element.setAttribute('download', 'stc-bookmarks.json')
      element.style.display = 'none'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
    },
    async set_page (new_page: number) {
      if (new_page < 1) {
        new_page = 1
      } else {
        this.page = new_page
        await this.submit()
      }
    },
    async submit () {
      this.is_loading = true
      try {
        const new_documents = []
        const bookmarks = this.bookmarks.slice(
          (this.page - 1) * this.page_size,
          this.page * this.page_size
        )
        for (const load_bookmark of bookmarks) {
          const collector_outputs = await this.search_service.custom_search(load_bookmark.query, {
            page: 1,
            index_name: load_bookmark.index_name
          })
          new_documents.push(
            collector_outputs[0].collector_output.documents.scored_documents[0]
          )
        }
        this.documents = new_documents
      } catch (e) {
        console.error(e)
        this.loading_failure_reason = e
      } finally {
        this.is_loading = false
      }
    }
  }
})
</script>
