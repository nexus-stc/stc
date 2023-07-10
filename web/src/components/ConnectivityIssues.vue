<template lang="pug">
div.font-monospace
  p {{ text }}
</template>

<script lang="ts">
import { defineComponent, toRaw } from "vue";
import { utils } from "summa-wasm";
import {get_label} from "@/translations";

export default defineComponent({
  name: "ConnectivityIssues",
  props: {
    reason: Error,
  },
  computed: {
    text() {
      if (this.reason && `${this.reason}`.startsWith("CompileError")) {
        return get_label("unsupported_browser");
      } else if (
        this.reason &&
        (this.reason.name === "AxiosError" ||
          `${this.reason}`.includes('\\"status\\":0') ||
          `${this.reason}`.includes("EOF while parsing a value"))
      ) {
        if (this.is_localhost) {
          return get_label('is_ipfs_enabled');
        } else {
          return get_label('network_error');
        }
      }
      return this.reason;
    },
    is_localhost() {
      return utils.get_ipfs_url().includes("localhost");
    },
  },
});
</script>
