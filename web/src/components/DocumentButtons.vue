<template lang="pug">
div
  .btn-group.btn-group-sm(v-if="files.length > 0 && files[0].external_links.length > 0")
    button.btn.btn-secondary(data-bs-toggle="modal" data-bs-target="#qr-modal")
      i.bi.bi-qr-code-scan
  .btn-group.btn-group-sm.ms-2
    button.btn.btn-secondary(v-if="!bookmark" @click.stop.prevent="add_bookmark")
      i.bi.bi-bookmark
    button.btn.btn-secondary(v-else @click.stop.prevent="remove_bookmark")
      i.bi.bi-bookmark-check-fill
  span(v-for="(file, index) in files")
    .btn-group.btn-group-sm.dropup(v-if="file.external_links.length > 0").ms-2
      a.btn.btn-secondary(type="button" :href="file.external_links[0].url" target="_blank")
        i.bi.bi-cloud-download-fill.me-2.ms-2 &nbsp;{{ file.label }}
      button.btn.btn-secondary.dropdown-toggle.dropdown-toggle-split.ms-1(v-if="file.external_links.length > 1" type="button", data-bs-toggle="dropdown" aria-expanded="false")
        span.visually-hidden.ms-1.me-1 Toggle Dropdown
      ul.dropdown-menu(v-if="file.external_links.length > 1")
        li(v-for="external_link of file.external_links")
          a.dropdown-item(:href="external_link.url" target="_blank") {{ external_link.name }}
  .modal.fade(v-if="files.length > 0 && files[0].external_links.length > 0" id="qr-modal" tabindex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true")
    .modal-dialog
      .modal-content
        .modal-header
          h5.modal-title IPFS Link
          button.btn-close(type="button" data-bs-dismiss="modal" aria-label="Close")
        div.modal-body
          qr-code(:url="'https://ipfs.io/ipfs/' + files[0].cid")
</template>

<script lang="ts">
// @ts-nocheck

import { useObservable } from '@vueuse/rxjs'
import { liveQuery } from 'dexie'
import { defineComponent, type PropType } from 'vue'

import { Bookmark, user_db } from '@/database'

import QrCode from './QrCode.vue'
import {format_bytes} from "@/utils";

export default defineComponent({
  name: 'DocumentButtons',
  components: { QrCode },
  props: {
    query: {
      type: String,
      required: true
    },
    files: {
      type: Array as PropType<Array<{label: string, cid: string, external_links: Array<{ url: string, name: string }>}>>
    }
  },
  data () {
    return {
      bookmark: useObservable(
        liveQuery(async () => {
          return await user_db.bookmarks.get({
            index_name: 'nexus_science',
            query: this.query
          })
        })
      )
    }
  },
  methods: {
    async add_bookmark () {
      await user_db.add_bookmark(new Bookmark("nexus_science", this.query))
    },
    async remove_bookmark () {
      await user_db.delete_bookmark("nexus_science", this.query)
    }
  }
})
</script>
