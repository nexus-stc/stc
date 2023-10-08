<template lang="pug">
.container
  .row
    .col-md-4.col-lg-3.mb-3
      ul.nav.flex-column.mb-auto
        li.nav-item
          router-link.btn.text-nowrap(to="/help")
            i.bi.bi-house
            span.ms-2 Welcome
        li.nav-item
          router-link.btn.text-nowrap(to="/help/how-to-search")
            i.bi.bi-question-circle-fill
            span.ms-2 {{ get_label("how_to_search") }}
        li.nav-item
          router-link.btn.text-nowrap(to="/help/donate")
            i.bi.bi-currency-dollar
            span.ms-2 {{ get_label("donate") }}
        hr
        li.nav-item
          button.btn.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#projects-collapse")
            i.bi.bi-caret-down
            span.ms-2 Projects
          .collapse.ms-3(id="projects-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/web" target="_blank")
                  i.bi.bi-globe
                  span.ms-2 Web STC
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/geck" target="_blank")
                  i.bi.bi-tools
                  span.ms-2 GECK
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/cybrex" target="_blank")
                  i.bi.bi-cpu
                  span.ms-2 Cybrex AI
              li.nav-item
                router-link.nav-link.text-secondary(to="/help/stc-hub-api")
                  i.bi.bi-app
                  span.ms-2 STC Hub API
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/tgbot" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Telegram Bots
        li.nav-item
          button.btn.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#guides-collapse")
            i.bi.bi-caret-down
            span.ms-2 Guides
          .collapse.ms-3(id="guides-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1
              li.nav-item
                router-link.nav-link.text-secondary(to="/help/install-ipfs")
                  i.bi.bi-box
                  span.ms-2 {{ get_label("install_ipfs") }}
              li.nav-item
                router-link.nav-link.text-secondary(to="/help/stc-box")
                  i.bi.bi-book
                  span.ms-2 {{ get_label("stc_box") }}
              li.nav-item
                router-link.nav-link.text-secondary(to="/help/replicate")
                  i.bi.bi-cloud-download
                  span.ms-2 {{ get_label("set_up_your_own_replica") }}
              li.nav-item
                router-link.nav-link.text-secondary(to="/help/doomsday")
                  i.bi.bi-radioactive
                  span.ms-2 Doomsday Guide
        li.nav-item
          button.btn.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#cids-collapse")
            i.bi.bi-caret-down
            span.ms-2 Links
          .collapse.ms-3.show(id="links-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://twitter.com/the_superpirate" target="_blank")
                  i.bi.bi-twitter
                  span.ms-2 Twitter
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://kolektiva.social/@the_superpirate" target="_blank")
                  i.bi.bi-mastodon
                  span.ms-2 Mastodon
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/+wN8n75kr4nxlMmZi" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Support
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/nexus_search" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 News
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/+nZLdjlcRKwY3MTBk" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Communities
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/science_nexus_bot" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Bot
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://github.com/nexus-stc/stc" target="_blank")
                  i.bi.bi-github
                  span.ms-2 GitHub
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="mailto:ultranymous@proton.me" target="_blank")
                  i.bi.bi-mailbox
                  span.ms-2 ultranymous@proton.me
        hr
    .col-md-8.col-lg-8
      router-view(id="hrv")
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'HelpView',
  created () {
    document.title = 'Help - STC'
  }
})
</script>
<style scoped lang="scss">
.router-link-exact-active {
  filter: brightness(150%);
}
</style>
