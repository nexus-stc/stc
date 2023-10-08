<template lang="pug">
.container
  h3 {{ get_label('install_ipfs') }}
  span(v-html="get_label('install_ipfs_content')")
</template>
<script lang="ts">
import { defineComponent } from 'vue'
import { get_label } from "@/translations";

export default defineComponent({
  name: 'InstallIpfsView',
  created () {
    document.title = `${get_label('install_ipfs')} - Help - STC`
  }
})
</script>
