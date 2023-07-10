<template lang="pug">
.container
  h2 Welcome, reader!
  p 欢迎读者！- आपका स्वागत है पाठक! - ¡Bienvenido lector! - Bienvenue lecteur! - مرحبًا بالقارئ! - Добро пожаловать, читатель!
  ul
    li
      a(href="/#/nexus_science/cid:bafykbzaceayxkpz5tk6nuqjzoidix4y4lakfwvzkmfisycduijcwfew7waa5e") English through pictures
    li
      a(href="/#/?q=english+for+beginners&p=1&d=nexus_science") Further sources for learning English
  h3 Search
  span(v-html="get_label('help')")
  h3 Pinning
  figure.text-center.mt-4
    blockquote.blockquote
      p
        span.font-monospace ipfs pin add /ipns/standard-template-construct.org --progress
    figcaption.blockquote-footer Pin database
  figure.text-center.mt-2
    blockquote.blockquote
      p
        span.font-monospace ipfs pin add /ipns/hub.standard-template-construct.org --progress
    figcaption.blockquote-footer Pin papers (require multi-TB disk space)
  h3 API
  ul
    li <a href="https://github.com/nexus-stc/stc/tree/master/geck">GECK</a> (Garden of Eden Creation Kit)
    li STC Hub Endpoint:
      p.font-monospace ipfs get /ipns/hub.standard-template-construct.org/{urlencode(doi)}.pdf
  h3 Contacts
  ul
    li <a href="https://twitter.com/the_superpirate">Twitter</a>, <a href="https://kolektiva.social/@the_superpirate">Mastodon</a> or email <code>ultranymous at proton dot me</code>
    li Nexus People in <a href="https://t.me/nexus_search">Telegram</a> and <a href="https://t.me/+wN8n75kr4nxlMmZi">related chat</a>
  hr
  img.img-fluid(id = "origin", src="@/assets/origin.jpg")
</template>
<script lang="ts">
import { defineComponent } from "vue";
export default defineComponent({
  name: "HelpView",
  created() {
    document.title = `Help - STC`;
  },
});
</script>
