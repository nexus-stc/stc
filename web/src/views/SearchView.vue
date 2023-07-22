<template lang="pug">
.container
  .row
    .col-md-8.offset-md-2
      div(v-if="is_loading" style="margin-top: 140px")
        loading-spinner(:label="search_service.current_init_status.value")
      div(v-else-if="loading_failure_reason !== undefined")
        connectivity-issues-view(:reason="loading_failure_reason")
      div(v-else)
        div.float-end.small.mb-1
          a.small(href="#/help/how-to-search" target=_blank) How to search?
        form(@submit.stop.prevent="on_search")
          div.input-group
            input.form-control.form-control-md(v-model="query" type="search" :placeholder="get_label('search_placeholder')" autofocus)
        div
          .mt-3
          form.row.g-3
            .col-lg-3.col-6
              select.form-select.form-select-sm(v-model="selected_index_name" @change="set_page(1)")
                option(v-for="enabled_index in enabled_indices" :value="enabled_index") {{ display_names[enabled_index] }}
            .col-lg-3.col-6
              select.form-select.form-select-sm(v-model="selected_language" @change="set_page(1)")
                option(v-for="enabled_language in enabled_languages" :value="enabled_language") {{ display_languages[enabled_language] }}
          div(v-if="total_documents !== null")
            hr
            i.small.ms-3 {{ total_documents }} {{ get_label('found') }}
        div.mt-5(v-if="!search_used")
          items-showcase
        div(v-else-if="is_documents_loading" style="margin-top: 140px")
          loading-spinner(:label="get_label('loading') + '...'")
        div(v-else-if="loading_documents_failure_reason !== undefined")
          connectivity-issues-view(:reason="loading_documents_failure_reason")
        div.mt-3.mb-3(v-else)
          search-list(:scored_documents='scored_documents')
          nav(v-if="has_next || page > 1")
            ul.pagination.justify-content-center
              li.page-item(v-if="page > 2" v-on:click="set_page(1);")
                a.page-link &lt;&lt;
              li.page-item(v-on:click="set_page(page - 1);")
                a.page-link &lt;
              li.page-item.disabled
                a.page-link {{ page }}
              li.page-item(v-if="has_next", v-on:click="set_page(page + 1);")
                a.page-link &gt;
</template>

<script lang="ts">
import { useObservable } from '@vueuse/rxjs'
import { liveQuery } from 'dexie'
import { defineComponent } from 'vue'
import { RouterLink } from 'vue-router'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import NexusFreeDocument from '@/components/document/NexusFree.vue'
import NexusMediaDocument from '@/components/document/NexusMedia.vue'
import NexusScienceDocument from '@/components/document/NexusScience.vue'
import ItemsShowcase from '@/components/ItemsShowcase.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SearchList from '@/components/SearchList.vue'
import { meta_db } from '@/database'
import { get_label } from '@/translations'

export default defineComponent({
  name: 'SearchView',
  components: {
    ItemsShowcase,
    ConnectivityIssuesView,
    LoadingSpinner,
    NexusFreeDocument,
    NexusMediaDocument,
    NexusScienceDocument,
    RouterLink,
    SearchList
  },
  props: {
    p: {
      type: Number
    },
    q: {
      type: String
    },
    d: {
      type: String
    },
    l: {
      type: String
    },
    ds: {
      type: Boolean
    }
  },
  data () {
    return {
      page: Number.parseInt((this.$route.query.p ?? 1).toString()),
      query: this.$route.query.q,
      selected_index_name: this.$route.query.d,
      selected_language: this.$route.query.l,
      index_configs: useObservable(
        liveQuery(async () => {
          return meta_db.index_configs.toArray()
        })
      ),
      is_loading: false,
      is_documents_loading: false,
      loading_documents_failure_reason: undefined,
      loading_failure_reason: undefined,
      scored_documents: [],
      search_used: false,
      total_documents: null,
      has_next: false,
      enabled_indices: [undefined],
      enabled_languages: [undefined, 'en', 'ar', 'pb', 'zh', 'am', 'fa', 'de', 'hi', 'id', 'it', 'ja', 'ms', 'ru', 'es', 'tg', 'uk', 'uz'],
      date_sorting: this.$route.query.ds === 'true',
      display_names: {
        undefined: get_label('everywhere'),
        nexus_free: '♾️ Free',
        nexus_media: '🧲 Media',
        nexus_science: '🔬 Science'
      },
      display_languages: {
        undefined: get_label('all_languages'),
        en: '🇬🇧 English',
        ar: '🇦🇪 Arabic',
        pb: '🇧🇷 Brazilian Portuguese',
        zh: '🇨🇳 Chinese',
        am: '🇪🇹 Ethiopian',
        fa: '🇮🇷 Farsi',
        de: '🇩🇪 German',
        hi: '🇮🇳 Hindi',
        id: '🇮🇩 Indonesian',
        it: '🇮🇹 Italian',
        ja: '🇯🇵 Japanese',
        ms: '🇲🇾 Malay',
        ru: '🇷🇺 Russian',
        es: '🇪🇸 Spanish',
        tg: '🇹🇯 Tajik',
        uk: '🇺🇦 Ukrainian',
        uz: '🇺🇿 Uzbek'
      }
    }
  },
  watch: {
    $route () {
      this.load_params()
      void this.submit()
    }
  },
  async created () {
    try {
      this.is_loading = true
      this.enabled_indices.push(
        ...(await this.search_service.get_enabled_index_configs()).map(
          (index_config) => index_config.index_name
        )
      )
    } catch (e) {
      console.error(e)
      this.loading_failure_reason = e
    } finally {
      this.is_loading = false
    }
    await this.submit()
  },
  methods: {
    load_params () {
      this.page = Number.parseInt((this.$route.query.p ?? 1).toString())
      this.query = this.$route.query.q
      this.selected_index_name = this.$route.query.d
      this.selected_language = this.$route.query.l
      this.date_sorting = this.$route.query.ds === 'true'
    },
    on_search (e: any) {
      this.date_sorting = false
      void this.set_page(1)
    },
    async set_page (new_page: number) {
      if (new_page < 1) {
        new_page = 1
      } else {
        void this.$router.push({
          name: 'search',
          query: {
            q: this.query,
            p: new_page,
            d: this.selected_index_name,
            l: this.selected_language,
            ds: this.date_sorting
          }
        })
      }
    },
    remove_query () {
      this.scored_documents = []
      this.total_documents = null
      this.has_next = false
      this.date_sorting = false
      document.title = 'STC'
    },
    async submit () {
      if ((this.query ?? '') === '') {
        this.search_used = false
        this.remove_query(); return
      }
      document.title = `${this.query} - STC`
      this.total_documents = null
      this.is_documents_loading = true
      this.search_used = true
      try {
        const collector_outputs = await this.search_service.custom_search(
          this.query,
          {
            index_name: this.selected_index_name,
            page: this.page,
            language: this.selected_language,
            date_sorting: this.date_sorting
          }
        )
        this.scored_documents =
          collector_outputs[0].collector_output.documents.scored_documents
        this.total_documents =
          collector_outputs[1].collector_output.count.count
        this.has_next = collector_outputs[0].collector_output.documents.has_next
        // Pre-fetch next page
        if (this.page > 1 && this.has_next) {
          this.search_service.custom_search(this.query, {
            index_name: this.selected_index_name,
            page: this.page + 1,
            language: this.selected_language,
            date_sorting: this.date_sorting
          })
        }
      } catch (e) {
        console.error(e)
        this.loading_documents_failure_reason = e
      } finally {
        this.is_documents_loading = false
      }
    }
  }
})
</script>
