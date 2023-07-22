<template lang="pug">
div.font-monospace
  p {{ text }}
</template>

<script lang="ts">
import { utils } from 'summa-wasm'
import { defineComponent } from 'vue'

import { get_label } from '@/translations'

export default defineComponent({
  name: 'ConnectivityIssues',
  props: {
    reason: {
      type: Error
    }
  },
  computed: {
    text () {
      if (this.reason?.toString().startsWith('CompileError')) {
        return get_label('unsupported_browser')
      } else if (
        (this.reason?.name === 'AxiosError' ||
          this.reason?.toString().includes('\\"status\\":0') ||
          this.reason?.toString().includes('EOF while parsing a value'))
      ) {
        if (this.is_localhost) {
          return get_label('is_ipfs_enabled')
        } else {
          return get_label('network_error')
        }
      }
      return this.reason
    },
    is_localhost () {
      return utils.get_ipfs_url().includes('localhost')
    }
  }
})
</script>
