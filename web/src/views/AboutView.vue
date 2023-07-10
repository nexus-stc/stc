<template lang="pug">
.container
  h4 {{ get_label('about') }}
  .alert.alert-warning(role="alert" v-html="get_label('about_alert')" )
  span(v-html="get_label('about_intro')")
  h4 {{ get_label('about_why') }}
  ul.mt-3(v-html="get_label('about_why_points')")
  span(v-html="get_label('about_end')")

  h4 {{ get_label("contacts") }}
  ul
    li <a href="https://twitter.com/the_superpirate">Twitter</a>, <a href="https://kolektiva.social/@the_superpirate">Mastodon</a> or email <code>ultranymous at proton dot me</code>
    li Nexus People in <a href="https://t.me/nexus_search">Telegram</a> and <a href="https://t.me/+wN8n75kr4nxlMmZi">related chat</a>
  hr
  img.img-fluid(id = "origin", src="@/assets/origin.jpg")
</template>
<script lang="ts">
import { defineComponent } from "vue";
import {get_label} from "../translations";
export default defineComponent({
  name: "AboutView",
  methods: {get_label},
  created() {
    document.title = `About - STC`;
    document.querySelector('head meta[name="description"]')!.setAttribute('content', get_label('about_intro'));
  },
});
</script>

<style lang="scss" scoped>
#origin {
  border-width: 20px;
  border-radius: 20px;
  border-color: #111111;
  border-style: solid;
}
</style>
