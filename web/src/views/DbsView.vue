<template lang="pug">
div(v-if="is_loading" style="margin-top: 140px")
  loading-spinner(label="loading databases...")
div(v-else)
  h4 Databases
  .col(v-for="index_config of index_configs")
    .card.h-100.mt-3
      .card-body
        h5.card-title.font-monospace {{ `${index_config.index_name} v.${format_date(index_config.created_at)}` }}
        .card-body.small
          .row(v-if="index_config.description")
            .card-text {{ index_config.description  }}
          .row
            hr.mt-4
            b Fields
            .card-text {{ index_fields.get(index_config.index_name).join(", ") }}
          .row
            hr.mt-4
            b Index ID
            .form-text
              span.lh-1 {{ index_config.index_seed }}
          .row
            hr.mt-4
            b Options
              .container
                .row.mt-3
                  .form-check.col-4
                    input.form-check-input(type="checkbox" :id="'checkbox_enabled_' + index_config.index_alias" v-model="index_config.index_properties.is_enabled" @change="save(index_config)")
                    label.form-check-label(:for="'checkbox_enabled_' + index_config.index_alias") Enabled
                .row
                  .form-check.col-4
                    input.form-check-input(type="checkbox" :id="'checkbox_is_exact_matches_promoted_' + index_config.index_alias" v-model="index_config.index_properties.is_exact_matches_promoted" @change="save(index_config)")
                    label.form-check-label(:for="'checkbox_is_exact_matches_promoted_' + index_config.index_alias") Exact matches
                  .form-check.col-4
                    input.form-check-input(type="checkbox" :id="'checkbox_is_fieldnorms_scoring_enabled_' + index_config.index_alias" v-model="index_config.index_properties.is_fieldnorms_scoring_enabled" @change="save(index_config)")
                    label.form-check-label(:for="'checkbox_is_fieldnorms_scoring_enabled_' + index_config.index_alias") Fieldnorms
                  .form-check.col-4
                    input.form-check-input(type="checkbox" :id="'checkbox_is_temporal_scoring_enabled_' + index_config.index_alias" v-model="index_config.index_properties.is_temporal_scoring_enabled" @change="save(index_config)")
                    label.form-check-label(:for="'checkbox_is_temporal_scoring_enabled_' + index_config.index_alias") Temporal
  div
    hr
    h4 Options legend
    .small.mt-4
      table.table.small
        thead
          tr
            th Option / Impact
            th First query penalty
            th Per query traffic
            th Memory
            th Support mobiles
        tbody
          tr
            th Exact matches
            td no
            td low
            td no
            td yes
          tr
            th Fieldnorms
            td high
            td no
            td high
            td no
          tr
            th Temporal
            td medium
            td no
            td high
            td no
</template>

<script lang="ts">
// @ts-nocheck
import { useObservable } from '@vueuse/rxjs'
import { liveQuery } from 'dexie'
import type { IndexConfig } from 'summa-wasm'
import { defineComponent, toRaw } from 'vue'

import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { meta_db } from '@/database'
import { format_bytes, format_date } from '@/utils'

export default defineComponent({
  name: 'DatabasesView',
  components: { LoadingSpinner },
  data () {
    return {
      index_configs: [],
      index_fields: new Map<string, string[]>(),
      is_loading: false,
      new_index_ipns_path: ''
    }
  },
  async created () {
    document.title = 'DBs - STC'
    this.is_loading = true
    this.index_configs = useObservable(
      liveQuery(async () => {
        const index_configs = await meta_db.index_configs.toArray()
        for (const index_config of index_configs) {
          this.index_fields.set(
            index_config.index_name,
            await this.search_service.remote_index_registry.get_index_field_names(
              index_config.index_name
            )
          )
        }
        return index_configs
      })
    )
    this.is_loading = false
  },
  methods: {
    format_bytes,
    format_date,
    save (index_config: IndexConfig) {
      void meta_db.save(toRaw(index_config))
    }
  }
})
</script>
