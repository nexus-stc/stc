<template lang="pug">
div.inversion-filter(id="epub-reader" ref="reader")
</template>

<script lang="ts">
import {defineComponent, type PropType} from 'vue'

import ePub from "epubjs";
import router from "@/router";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import {get_label} from "@/translations";
import Hammer from 'hammerjs'


export default defineComponent({
  name: 'EpubReader',
  emits: ["update-anchor"],
  components: {ConnectivityIssuesView, LoadingSpinner},
  props: {
    anchor: {
      type: undefined as PropType<string> | undefined
    },
    data: {
      type: undefined as PropType<ArrayBuffer> | undefined
    },
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
    const book = ePub();
    await book.open(this.data)
    await book.ready;

    this.rendition = book.renderTo(
        "epub-reader", {
          flow: "paginated",
          method: "continuous",
          width: "100%",
          height: "100%",
          resizeOnOrientationChange: true,
          allowScriptedContent: true,
        });

    this.rendition.on("locationChanged", (e) => {
      let anchor = undefined;
      if (e !== undefined) {
        anchor = e.start;
      }
      this.$emit('update-anchor', anchor);
    });
    this.rendition.on("rendered", (e) => {
      const iframe = document.querySelector('iframe').contentDocument;
      const hammer = Hammer(iframe.body, { touchAction : 'auto' });
      hammer.get('swipe').set({ direction: Hammer.DIRECTION_HORIZONTAL })
      hammer.get('pan').set({ direction: Hammer.DIRECTION_ALL });
      hammer.get('pinch').set({ enable: true });
      hammer.on('panstart panmove', (ev) => ev.preventDefault());
      hammer.on('swipeleft', () => this.rendition.prev());
      hammer.on('swiperight', () => this.rendition.next());
      iframe.addEventListener("keyup", this.key_listener, {capture: true});
    });
    this.setup_theme_processor();
    await this.rendition.display(this.anchor);
  },
  mounted() {
    document.addEventListener("keyup", this.key_listener, {capture: true})
    this.mounted = true
  },
  beforeUnmount() {
    if (this.mounted) {
      document.removeEventListener("keyup", this.key_listener, {capture: true});
      this.$refs.reader.removeEventListener("keyup", this.key_listener, {capture: true});
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
    }
  }
})
</script>
<style lang="scss" scoped>
#epub-reader {
  position: fixed;
  min-width: 100%;
  width: 100%;
  min-height: calc(100% - 126px);
  height: calc(100% - 126px);
}
</style>
