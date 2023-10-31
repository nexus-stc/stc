<template lang="pug">
div
  .btn-group.btn-group-sm(v-if="http_links.get_best_file_links_groups() !== undefined")
    button.btn.btn-secondary(@click.stop.prevent="launch_reader")
      i.bi.bi-book
  .btn-group.btn-group-sm.ms-2(v-if="http_links.first_file_links_group_first_external_link()")
    button.btn.btn-secondary(data-bs-toggle="modal" data-bs-target="#qr-modal")
      i.bi.bi-qr-code-scan
  .btn-group.btn-group-sm.ms-2
    button.btn.btn-secondary(v-if="!bookmark" @click.stop.prevent="add_bookmark")
      i.bi.bi-bookmark
    button.btn.btn-secondary(v-else @click.stop.prevent="remove_bookmark")
      i.bi.bi-bookmark-check-fill
  span
    .btn-group.btn-group-sm.dropup(v-if="http_links.file_links_groups.length > 0").ms-2
      a.btn.btn-secondary(type="button" :href="http_links.first_file_links_group().first_link().url + '&download=true'" target="_blank")
        i.bi.bi-cloud-download-fill.me-2.ms-2 &nbsp; {{ http_links.first_file_links_group().label }}
      button.btn.btn-secondary.dropdown-toggle.dropdown-toggle-split.ms-1(v-if="http_links.file_links_groups.length > 1" type="button", data-bs-toggle="dropdown" aria-expanded="false")
        span.visually-hidden.ms-1.me-1 Toggle Dropdown
      ul.dropdown-menu(v-if="http_links.file_links_groups.length > 1")
        li(v-for="(file_links_group, index) in http_links.file_links_groups")
          a.dropdown-item(:href="file_links_group.first_link().url + '&download=true'" target="_blank") {{ file_links_group.label }}
  .modal.fade(v-if="http_links.first_file_links_group_first_external_link()" id="qr-modal" tabindex="-1" aria-labelledby="exampleModalLabel" aria-hidden="true")
    .modal-dialog
      .modal-content
        .modal-header
          h5.modal-title IPFS Link
          button.btn-close(type="button" data-bs-dismiss="modal" aria-label="Close")
        div.modal-body
          qr-code(:url="http_links.first_file_links_group_first_external_link().url")

</template>

<script lang="ts">
// @ts-nocheck

import { useObservable } from '@vueuse/rxjs'
import { liveQuery } from 'dexie'
import { defineComponent, type PropType } from 'vue'

import { Bookmark, user_db } from '@/database'

import QrCode from './QrCode.vue'
import {format_bytes} from "@/utils";
import {HttpLinks} from "@/components/BaseDocument.vue";

export default defineComponent({
  name: 'DocumentButtons',
  components: { QrCode },
  props: {
    query: {
      type: String,
      required: true
    },
    http_links: {
      type: HttpLinks
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
    async launch_reader () {
      const best_link = this.http_links.get_best_file_links_groups()
      if (best_link) {
        if (!best_link.filename.endsWith("pdf") && !best_link.filename.endsWith("epub") && !best_link.filename.endsWith("djvu")) {
          return;
        }
        this.$router.push({
            name: 'reader',
            query: {
              cid: best_link.cid,
              filename: best_link.filename,
            }
          })
          return;
      }
    },
    async remove_bookmark () {
      await user_db.delete_bookmark("nexus_science", this.query)
    }
  }
})
</script>
