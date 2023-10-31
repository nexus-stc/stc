<template lang="pug">
.container.col-md-8.offset-md-2(v-if="is_rendering")
  loading-spinner(style="margin-top: 140px" :label="'rendering...'")
div(ref="wrapper")
  canvas(v-show="!is_rendering" id="djvu-reader" ref="reader")
</template>

<script lang="ts">
import {defineComponent, type PropType, toRaw} from 'vue'

import router from "@/router";
import ConnectivityIssuesView from "@/components/ConnectivityIssues.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import DjVu from "@/components/djvu";
import Hammer from 'hammerjs'


export default defineComponent({
  name: 'DjvuReader',
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
      hammer: undefined,
      current_page: 1,
      mounted: false,
      scale: 0.8,
      worker: undefined,
    }
    if (this.anchor !== undefined) {
      d.current_page = Number.parseInt(this.anchor);
    }
    return d;
  },
  async created() {
    this.worker = new DjVu.Worker();
    await toRaw(this.worker).createDocument(this.data, undefined);
    await this.render(undefined);
  },
  mounted() {
    this.hammer = Hammer(this.$refs.reader, { touchAction : 'auto' });
    document.addEventListener("keyup", this.key_listener);
    this.hammer.get('swipe').set({ direction: Hammer.DIRECTION_HORIZONTAL })
    this.hammer.get('pan').set({ direction: Hammer.DIRECTION_ALL });
    this.hammer.get('pinch').set({ enable: true });
    this.hammer.on('panstart panmove', (ev) => ev.preventDefault());
    this.hammer.on('swipeleft', () => this.previous_page());
    this.hammer.on('swiperight', () => this.next_page());
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
      this.is_rendering = true;
      try {
        const resultImageData = await toRaw(this.worker).doc.getPage(this.current_page).getImageData().run();
        this.$refs.reader.width = resultImageData.width;
        this.$refs.reader.height = resultImageData.height;
        this.$refs.reader.style.width = `${100 * this.scale}%`
        this.$refs.reader.style['min-width'] = `${100 * this.scale}%`

        const context = this.$refs.reader.getContext('2d');
        context.putImageData(resultImageData, 0, 0);
        this.$emit("update-anchor", this.current_page.toString())
      } catch {
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
  }
})
</script>
<style lang="scss" scoped>
#djvu-reader {
  display: block;
  margin-left: auto;
  margin-right: auto;
  min-width: 100%;
  width: 100%;
}
</style>
