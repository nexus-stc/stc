<template lang="pug">
.container
  h3 Install IPFS
  p The Standard Template Construct (STC) is distributed through IPFS, an uncensorable distributed network. When using STC, you download portions of the library from multiple peers to your local computer for offline use.
  p You may have accessed this page through the public gateway. While this method is convenient, it's not always reliable because public gateways can potentially censor this site.
  p You'll need to install and configure specific software on your computer to access this site directly from the IPFS network.
  h5 Step 1: Install IPFS Desktop
  p Follow the <a href="https://docs.ipfs.tech/install/ipfs-desktop/" target="_blank">official guide</a> to install IPFS Desktop.
  h5 Step 2: Install IPFS Companion for Your Browser
  p The IPFS Companion is a browser extension that provides a smoother experience with IPFS. Follow the <a href="https://docs.ipfs.tech/install/ipfs-companion/" target="_blank">official guide</a> to install the appropriate extension for your browser.
</template>
<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'InstallIpfsView',
  created () {
    document.title = 'Install IPFS - Help - STC'
  }
})
</script>
