<script lang="ts">
import { defineComponent } from 'vue'

import TagsList from '../TagsList.vue'
import BaseDocument from './Document.vue'

export default defineComponent({
  name: 'BaseNexusMedia',
  components: { TagsList },
  extends: BaseDocument,
  data () {
    return {
      index_name: 'nexus_media'
    }
  },
  computed: {
    coordinates () {
      const parts = []
      if (this.formatted_date) {
        parts.push(this.formatted_date)
      }
      return parts.join(' ')
    },
    extras () {
      const parts = []
      if (this.document.size) {
        parts.push(this.format_bytes(this.document.size))
      }
      parts.push('🧲')
      return parts.join(' | ')
    },
    filesize () {
      return this.document.size
    },
    issued_at () {
      return this.document.registered_at
    },
    external_links () {
      return [
        {
          url: `magnet:?xt=urn:btih:${
            this.document.torrent_hash
          }&tr=${encodeURIComponent(this.tracker)}`,
          name: 'Magnet'
        }
      ]
    },
    tracker () {
      switch (this.document.torrent_tracker_id) {
        case 1:
          return 'http://bt.t-ru.org/ann?magnet'
        default:
          return `http://bt${this.document.torrent_tracker_id}.t-ru.org/ann?magnet`
      }
    }
  }
})
</script>

<style scoped lang="scss">
li {
  padding-bottom: 15px;
  padding-left: 0;
  &:after {
    content: none;
  }
}
</style>
