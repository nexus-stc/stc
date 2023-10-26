<template lang="pug">
.container
  .row
    .col-md-8.offset-md-2
      div(v-if="current_init_status !== undefined" style="margin-top: 140px")
        loading-spinner(:label="current_init_status")
      div(v-else)
        div.float-end.small.mb-1
          a(href="#/help/how-to-search" target="_blank") {{ get_label('how_to_search') }}
        form(@submit.stop.prevent="on_search")
          div.input-group
            input.form-control.form-control-md(v-model="query" type="search" :placeholder="get_label('search_placeholder')" autofocus)
        div
          .mt-3
          form.row.g-3
            .col-6.col-lg-3
              select.form-select.form-select(v-model="selected_type" @change="switch_parameter()")
                option(v-for="[type, display_type] of types" :value="type") {{ display_type }}
            .col-6.col-lg-4
              select.form-select.form-selectm(v-model="selected_language" @change="switch_parameter()")
                option(v-for="[language, display_language] of languages" :value="language") {{ display_language }}
            .col-6.col-lg-4
              select.form-select.form-selectm(v-model="selected_timerange" @change="switch_parameter()")
                option(v-for="[year, display_year] of years" :value="year") {{ display_year }}
            .col-6.col-lg-1
              h4.mt-1.me-2.text-end(v-if="!is_loading && !is_documents_loading" role="button" @click.stop.prevent="roll") 🎲
        div(v-if="is_documents_loading" style="margin-top: 140px")
          loading-spinner(:label="get_label('loading') + '...'")
        div(v-else-if="loading_documents_failure_reason !== undefined")
          connectivity-issues-view(:reason="loading_documents_failure_reason")
        div.mt-3(v-else)
          div(v-if="total_documents !== null || (has_next || page > 1) && !is_rolled")
            hr
            div.float-start(v-if="total_documents !== null")
              i.ms-3 {{ total_documents }} {{ get_label('found') }}
            nav(v-if="(has_next || page > 1) && !is_rolled")
              ul.pagination.pagination-lg.float-end
                li.page-item(v-if="page > 2" v-on:click="set_page(1);")
                  a.page-link &lt;&lt;
                li.page-item(v-on:click="set_page(page - 1);")
                  a.page-link &lt;
                li.page-item.disabled
                  a.page-link {{ page }}
                li.page-item(v-if="has_next", v-on:click="set_page(page + 1);")
                  a.page-link &gt;
            .clearfix
          search-list(:scored_documents='scored_documents')
          nav(v-if="(has_next || page > 1) && !is_rolled")
            ul.pagination.pagination-lg.justify-content-center
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
// @ts-nocheck
import {defineComponent} from 'vue'
import {RouterLink} from 'vue-router'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SearchList from '@/components/SearchList.vue'
import {Language, Type} from "@/services/search/query-processor";
import {get_label} from "@/translations";

function generate_year_ranges() {
  let ranges = [[undefined, get_label("all_times")]];
  let current_year = new Date().getFullYear();
  for (let shift of [0, 1, 2]) {
    const left_date = new Date(Date.UTC(current_year - shift, 0, 1));
    const right_date = new Date(Date.UTC(current_year - shift + 1, 0, 1));
    ranges.push([[left_date / 1000, right_date / 1000], (current_year - shift).toString()])
  }
  const right_date = new Date(Date.UTC(current_year - 2, 0, 1)) / 1000;
  ranges.push([[0, right_date], "Before " + (current_year - 2).toString()]);
  return ranges;
}

export default defineComponent({
  name: 'SearchView',
  components: {
    ConnectivityIssuesView,
    LoadingSpinner,
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
  data() {
    return {
      current_init_status: this.search_service.current_init_status,
      current_query_id: 0,
      has_next: false,
      page: Number.parseInt((this.$route.query.p ?? 1).toString()),
      query: this.$route.query.q,
      selected_timerange: this.$route.query.y,
      selected_type: this.$route.query.t,
      selected_language: this.$route.query.l,
      is_date_sorting_enabled: this.$route.query.ds === 'true',
      is_loading: false,
      is_rolled: false,
      is_documents_loading: false,
      languages: [[undefined, get_label("all_languages")], ...Object.entries(Language)],
      loading_documents_failure_reason: undefined,
      scored_documents: [],
      search_used: false,
      total_documents: null,
      types: [[undefined, get_label("all_types")], ...Object.entries(Type)],
      years: generate_year_ranges(),
    }
  },
  watch: {
    $route() {
      this.load_params()
      void this.submit()
    }
  },
  async created() {
    await this.submit()
  },
  methods: {
    load_params() {
      this.page = Number.parseInt((this.$route.query.p ?? 1).toString())
      this.query = this.$route.query.q
      this.selected_type = this.$route.query.t
      this.selected_language = this.$route.query.l
      this.selected_timerange = this.$route.query.y
      this.is_date_sorting_enabled = this.$route.query.ds === 'true'
    },
    on_search(e: any) {
      this.is_date_sorting_enabled = false
      this.is_rolled = false;
      void this.set_page(1)
    },
    async switch_parameter() {
      if (this.is_rolled && !this.query) {
        return await this.roll();
      }
      return await this.set_page(1);
    },
    async set_page(new_page: number) {
      if (new_page < 1) {
        new_page = 1
      } else {
        void this.$router.push({
          name: 'search',
          query: {
            q: this.query,
            p: new_page,
            t: this.selected_type,
            l: this.selected_language,
            y: this.selected_timerange,
            ds: this.is_date_sorting_enabled.toString()
          }
        })
      }
    },
    remove_query() {
      this.scored_documents = []
      this.total_documents = null
      this.has_next = false
      this.is_date_sorting_enabled = false
      document.title = 'STC'
    },
    async roll() {
      this.is_documents_loading = true;
      this.is_rolled = true;
      this.total_documents = null;
      this.current_query_id += 1;
      const guard = this.current_query_id.valueOf();
      const search_job = async () => {
        try {
          const collector_outputs = await this.search_service.search(this.query, {
            page: 1,
            type: this.selected_type,
            language: this.selected_language,
            timerange: this.selected_timerange,
            random: true,
          })
          if (guard == this.current_query_id) {
            this.scored_documents = collector_outputs[0].collector_output.documents.scored_documents
          }
        } catch (e) {
          if (guard == this.current_query_id) {
            this.loading_documents_failure_reason = e
          }
        } finally {
          if (guard == this.current_query_id) {
            this.is_documents_loading = false
          }
        }
      }
      search_job()
    },
    async submit() {
      if ((this.query ?? '') === '') {
        this.search_used = false
        this.remove_query();
        return
      }

      document.title = `${this.query} - STC`
      this.total_documents = null
      this.is_documents_loading = true
      this.search_used = true
      this.is_rolled = false;

      this.current_query_id += 1;
      const guard = this.current_query_id.valueOf();
      const search_job = async () => {
        try {
          const collector_outputs = await this.search_service.search(
              this.query,
              {
                type: this.selected_type,
                page: this.page,
                language: this.selected_language,
                timerange: this.selected_timerange,
                is_date_sorting_enabled: this.is_date_sorting_enabled
              }
          )
          if (guard == this.current_query_id) {
            this.scored_documents =
                collector_outputs[0].collector_output.documents.scored_documents
            this.total_documents =
                collector_outputs[1].collector_output.count.count
            this.has_next = collector_outputs[0].collector_output.documents.has_next
            // Pre-fetch next page
            if (this.page > 1 && this.has_next) {
              this.search_service.search(this.query, {
                type: this.selected_type,
                page: this.page + 1,
                language: this.selected_language,
                timerange: this.selected_timerange,
                is_date_sorting_enabled: this.is_date_sorting_enabled
              })
            }
          }
        } catch (e) {
          console.error(e)
          if (guard == this.current_query_id) {
            this.loading_documents_failure_reason = e
          }
        } finally {
          if (guard == this.current_query_id) {
            this.is_documents_loading = false
          }
        }
      };
      search_job();
    }
  }
})
</script>
