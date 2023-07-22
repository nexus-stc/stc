<template lang="pug">
.btn-group(v-if="external_links")
  button.btn.btn-secondary(data-bs-toggle="modal" data-bs-target="#qr-modal")
    i.bi.bi-qr-code-scan
.btn-group.ms-2
  button.btn.btn-secondary(v-if="!bookmark" @click.stop.prevent="add_bookmark")
    i.bi.bi-bookmark
  button.btn.btn-secondary(v-else @click.stop.prevent="remove_bookmark")
    i.bi.bi-bookmark-check-fill
.btn-group(v-if="external_links.length > 0").ms-2
  a.btn.btn-secondary(type="button" :href="external_links[0].url" target="_blank")
    i.bi.bi-cloud-download-fill.me-2.ms-2
  button.btn.btn-secondary.dropdown-toggle.dropdown-toggle-split.ms-1(v-if="external_links.length > 1" type="button", data-bs-toggle="dropdown" aria-expanded="false")
    span.visually-hidden.ms-1.me-1 Toggle Dropdown
  ul.dropdown-menu(v-if="external_links.length > 1")
    li(v-for="external_link of external_links")
      a.dropdown-item(:href="external_link.url" target="_blank") {{ external_link.name }}
.modal.fade(v-if="external_links" id="qr-modal" tabindex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true")
  .modal-dialog
    .modal-content
      .modal-header
        h5.modal-title IPFS Link
        button.btn-close(type="button" data-bs-dismiss="modal" aria-label="Close")
      div.modal-body
        qr-code(:url="'https://ipfs.io/ipfs/' + external_links[0].cid")
</template>

<script lang="ts">
import { useObservable } from '@vueuse/rxjs'
import { liveQuery } from 'dexie'
import { defineComponent, type PropType } from 'vue'

import { Bookmark, user_db } from '@/database'

import QrCode from './QrCode.vue'

export default defineComponent({
  name: 'DocumentButtons',
  components: { QrCode },
  props: {
    index_name: {
      type: String,
      required: true
    },
    query: {
      type: String,
      required: true
    },
    external_links: {
      type: Array as PropType<Array<{ url: string, name: string }>>
    }
  },
  data () {
    return {
      bookmark: useObservable(
        liveQuery(async () => {
          return await user_db.bookmarks.get({
            index_name: this.index_name,
            query: this.query
          })
        })
      )
    }
  },
  methods: {
    async add_bookmark () {
      await user_db.add_bookmark(new Bookmark(this.index_name, this.query))
    },
    async remove_bookmark () {
      await user_db.delete_bookmark(this.index_name, this.query)
    }
  }
})
</script>
