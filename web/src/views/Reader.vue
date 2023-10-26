<template lang="pug">
.container(v-if="error !== undefined")
  .row
    .col-md-8.offset-md-2
      connectivity-issues-view(:reason="error")
.container(v-else-if="downloading_status !== undefined")
  .row
    .col-md-8.offset-md-2
      loading-spinner(:label="downloading_status")
div.inversion-filter(v-else id="reader")
</template>

<script lang="ts">
import {defineComponent, type PropType, toRef} from 'vue'

import ePub from "epubjs";
import {cid_local_link} from "@/components/BaseDocument.vue";
import router from "@/router";
import {tracked_download} from "@/components/download-progress";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import {get_label} from "@/translations";

export default defineComponent({
  name: 'Reader',
  components: {ConnectivityIssuesView, LoadingSpinner},
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
      const book = ePub();
      await book.open(files[0])
      await book.ready;

      this.rendition = book.renderTo(
          "reader", {
            flow: "paginated",
            method: "continuous",
            width: "100%",
            height: "100%",
            resizeOnOrientationChange: true,
            allowScriptedContent: true,
            scale: 1.5,
          });
      this.rendition.on("locationChanged", (e) => {
        let anchor = undefined;
        if (e !== undefined) {
          anchor = e.start;
        }
        router.replace({
          name: 'reader',
          query: {
            cid: this.cid,
            filename: this.filename,
            anchor: anchor,
          }
        })
      });
      this.rendition.on("rendered", (e) => {
        const iframe = document.querySelector('iframe').contentDocument;
        iframe.addEventListener("keyup", this.key_listener, {capture: true});
        iframe.addEventListener("touchend", this.touch_listener, {capture: true});
      });
      this.setup_theme_processor();
      await this.rendition.display(this.anchor);
      document.addEventListener("keyup", this.key_listener, {capture: true})
      this.error = undefined
    } catch (e) {
      this.error = "The file cannot be loaded";
      return;
    }
  },
  mounted() {
    this.mounted = true
  },
  beforeUnmount() {
    if (this.mounted) {
      document.removeEventListener("keyup", this.key_listener, {capture: true});
      const reader = document.querySelector('#reader');
      if (reader) {
        reader.removeEventListener("keyup", this.key_listener, {capture: true})
      }
    }
    this.mounted = false;
  },
  methods: {
    setup_theme_processor() {
      // Color then inverted, so we have taken our main color and inverted it.
      this.rendition.themes.register("light", {});
      this.rendition.themes.register("dark",
          {
            "html": {"background-color": "rgb(216, 218, 222)"},
          });
      this.rendition.themes.select(window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light');
      let that = this;
      window
          .matchMedia('(prefers-color-scheme: dark)')
          .addEventListener('change', function updateTheme() {
            that.rendition.themes.select(window.matchMedia('(prefers-color-scheme: dark)').matches
                ? 'dark'
                : 'light');
          });
    },
    key_listener(event) {
      event.preventDefault();
      if (event.key == "ArrowLeft") {
        this.rendition.prev();
      } else if (event.key == "ArrowRight") {
        this.rendition.next();
      } else if (event.key === "Escape") {
        router.back();
        return;
      }
    },
    touch_listener(event) {
      event.preventDefault();
      const touch_end = event.changedTouches[0].screenX;
      if (touch_end < window.innerWidth / 2) {
        this.rendition.prev();
      } else {
        this.rendition.next();
      }
    },
  }
})
</script>
<style lang="scss" scoped>
#reader {
  position: fixed;
  min-width: 100%;
  width: 100%;
  min-height: calc(100% - 126px);
  height: calc(100% - 126px);
}
</style>
