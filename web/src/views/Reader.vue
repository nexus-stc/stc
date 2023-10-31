<template lang="pug">
.container(v-if="error !== undefined")
  .row
    .col-md-8.offset-md-2
      connectivity-issues-view(:reason="error")
.container.col-md-8.offset-md-2(v-else-if="downloading_status !== undefined")
  loading-spinner(style="margin-top: 140px" :label="downloading_status")
div(v-else-if="data !== undefined")
  epub-reader.inversion-filter(v-if="filename.endsWith('epub')" :anchor="anchor" :data="data" v-on:update-anchor="update_anchor")
  djvu-reader(v-else-if="filename.endsWith('djvu')" :anchor="anchor" :data="data" v-on:update-anchor="update_anchor")
  pdf-reader(v-else-if="filename.endsWith('pdf')" :anchor="anchor" :data="data" v-on:update-anchor="update_anchor")
</template>

<script lang="ts">
import {defineComponent, type PropType, toRef} from 'vue'

import {cid_local_link} from "@/components/BaseDocument.vue";
import router from "@/router";
import {tracked_download} from "@/components/download-progress";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import {get_label} from "@/translations";
import DjvuReader from "@/components/DjvuReader.vue";
import EpubReader from "@/components/EpubReader.vue";
import PdfReader from "@/components/PdfReader.vue";

export default defineComponent({
  name: 'Reader',
  components: {PdfReader, EpubReader, DjvuReader, ConnectivityIssuesView, LoadingSpinner},
  props: {
    cid: {
      type: undefined as PropType<string> | undefined
    },
    filename: {
      type: undefined as PropType<string> | undefined
    },
    anchor: {
      type: undefined as PropType<string> | undefined
    }
  },
  data() {
    return {
      data: undefined,
      downloading_status: get_label("loading") + "...",
      error: undefined,
      mounted: false,
      rendition: undefined,
    }
  },
  async created() {
    const local_link = cid_local_link(this.cid, this.filename);
    try {
      const files = await tracked_download([local_link.url], toRef(this, 'downloading_status'));
      this.data = files[0];
      this.error = undefined
    } catch (e) {
      this.error = e;
      return;
    }
  },
  methods: {
    update_anchor(new_anchor: string) {
      router.replace({
        name: 'reader',
        query: {
          cid: this.cid,
          filename: this.filename,
          anchor: new_anchor,
        }
      })
    },
  }
})
</script>
