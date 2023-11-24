<template lang="pug">
.container.col-md-8.offset-md-2(v-if="is_rendering")
  loading-spinner(style="margin-top: 140px" :label="'rendering...'")
canvas(v-show="!is_rendering" id="pdf-reader" ref="reader")
</template>

<script lang="ts">
import {defineComponent, type PropType, toRaw} from 'vue'

import router from "@/router";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import * as PdfJs from "pdfjs-dist";
import Hammer from 'hammerjs'

PdfJs.GlobalWorkerOptions.workerSrc = new URL(
    '~/pdfjs-dist/build/pdf.worker.js',
    import.meta.url
);

export default defineComponent({
  name: 'PdfReader',
  emits: ["update-anchor"],
  components: {ConnectivityIssuesView, LoadingSpinner},
  props: {
    anchor: undefined as PropType<string>,
    data: {
      type: undefined as PropType<ArrayBuffer>
    },
  },
  data() {
    let d = {
      is_rendering: false,
      current_page: 1,
      pdf_document: undefined,
      mounted: false,
      scale: 0.8,
      hammer: undefined,
    }
    if (this.anchor !== undefined) {
      d.current_page = Number.parseInt(this.anchor);
    }
    return d;
  },
  async created() {
    this.pdf_document = await PdfJs.getDocument(this.data).promise;
    await this.render(undefined);
  },
  mounted() {
    this.hammer = Hammer(this.$refs.reader, { touchAction : 'pan-y' });
    document.addEventListener("keyup", this.key_listener);
    this.hammer.get('swipe').set({ direction: Hammer.DIRECTION_HORIZONTAL })
    this.hammer.get('pan').set({ direction: Hammer.DIRECTION_ALL });
    this.hammer.get('pinch').set({ enable: true });
    this.hammer.on('panstart panmove', (ev) => ev.preventDefault());
    this.hammer.on('swipeleft', () => this.next_page());
    this.hammer.on('swiperight', () => this.previous_page());
    this.mounted = true
  },
  beforeUnmount() {
    if (this.mounted) {
      document.removeEventListener("keyup", this.key_listener, {capture: true});
      this.hammer.off("swipeleft");
      this.hammer.off("swiperight");
      this.hammer.off("panstart");
      this.hammer.off("panmove");
    }
    this.mounted = false;
  },
  methods: {
    async render(old_page) {
      if (this.is_rendering) {
        return;
      }
      this.is_rendering = true;
      try {
        const pdf_document = toRaw(this.pdf_document)
        const page = await pdf_document.getPage(this.current_page);
        const viewport = page.getViewport({ scale: window.devicePixelRatio * this.scale * 2, });
        this.$refs.reader.width = viewport.width;
        this.$refs.reader.height = viewport.height;
        this.$refs.reader.style.width = `${100 * this.scale}%`
        this.$refs.reader.style['min-width'] = `${100 * this.scale}%`
        const context = this.$refs.reader.getContext('2d');
        var renderContext = {
          canvasContext: context,
          viewport: viewport
        };
        page.render(renderContext);
        this.$emit("update-anchor", this.current_page.toString())
      } catch (e) {
        if (old_page !== undefined) {
          this.current_page = old_page;
        }
      }
      finally {
        this.is_rendering = false;
      }
    },
    previous_page() {
      const old_page = this.current_page;
      this.current_page -= 1;
      this.render(old_page);
    },
    next_page() {
      const old_page = this.current_page;
      this.current_page += 1;
      this.render(old_page);
    },
    key_listener(event) {
      event.preventDefault();
      if (event.key == "ArrowLeft") {
        this.previous_page()
      } else if (event.key == "ArrowRight") {
        this.next_page()
      } else if (event.key === "Escape") {
        router.back();
        return;
      }
    },
  },
})
</script>
<style lang="scss" scoped>
#pdf-reader {
  display: block;
  margin-left: auto;
  margin-right: auto;
  min-width: 100%;
  width: 100%;
}
</style>
