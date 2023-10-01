<template lang="pug">
.container
  h3 Build STC Box for Home or Library Use
  p You can set up STC on a small computer to act as a personal or group library.
  h5 Minimum Requirements
  p For testing, we used an Orange PI 5 with 16GB of RAM, a Sandisk 128GB MicroSD, and a 16TB Seagate Exos HDD attached externally by a USB cord, all of which demonstrated strong performance.
  p In general, you can use any computer with the following specs
  ul
    li A 4-core arm64 or x86-based CPU
    li 16GB RAM
    li 256GB+ of storage for the metadata database, 10TB+ for the entire dataset
  p If you are using Orange PI, take a note on power supply. We have experienced issues when attached HDD through USB3.0 but everything was all right after switching to left USB2.0.
  h5 System Configuration
  h6 Burning the MicroSD Card
  p Start by obtaining an OS image suitable for your hardware. Orange PI images can be downloaded from <a href="http://www.orangepi.org/html/serviceAndSupport/index.html" target="_blank">their official site</a>.
  p Burn the image file (usually *.iso or *.img) onto your MicroSD card. On MacOS and Linux, this can be done using the <code>dd</code> utility (set <code>if</code> and <code>of</code> to correspond to your file and disk respectively):
  pre
    code
      sudo dd if=file.img of=/dev/sde status=progress conv=fsync
  h6 IPFS Configuration
  p Follow Steps 1 and 2 from the <a href="#/help/replicate">replication guide</a> to set up IPFS.
  h5 Start Using It!
  p <a href="#/help/install-ipfs">Install IPFS</a> on any desktop in the same LAN, and then open <a href="http://standard-template-construct.org">STC</a>.
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'StcBoxView',
  created () {
    document.title = 'Create a Compact STC Box for Home or Library Use - Help - STC'
  }
})
</script>
