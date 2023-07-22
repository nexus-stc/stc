<template lang="pug">
.container
  h3 STC Hub API
  p The STC Hub API offers a straightforward way to integrate third-party applications with the STC's extensive corpus of scholarly publications.
  h5 Introduction
  p IPFS allows the creation of large, distributable directories across multiple peers. Each directory is assigned a unique CID that can be used as a reference.
  p We have utilized this feature to compile a directory of numerous scholarly papers, each labeled with its DOI. The entire directory can be accessed via the following alias: <code>/ipns/hub.standard-template-construct.org</code>
  p Users have the ability to pin this directory, locate a paper by its DOI, or directly retrieve papers from the directory.
  h5 Usage
  h6 Retrieving Files Through IPFS
  p All DOIs are urlencoded to accommodate special characters in the name. Below is an example of how to retrieve a paper using the Kubo CLI:
  code ipfs get /ipns/hub.standard-template-construct.org/10.1145%2F15922.15895.pdf
  h6 Retrieving Files Through HTTP API
  p The names are urlencoded twice due to the HTTP server decoding urlencoded URLs independently before passing them to the IPFS network:
  pre
    code
      | export IPNS_NAME=/ipns/hub.standard-template-construct.org
      | export GATEWAY_URL=http://localhost:8080
      | curl -L $GATEWAY_URL/$IPNS_NAME/10.1145%252F15922.15895.pdf
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'StcHubApiView',
  created () {
    document.title = 'STC Hub API - Help - STC'
  }
})
</script>
