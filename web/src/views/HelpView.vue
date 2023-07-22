<template lang="pug">
.container.small
  .row
    .col-md-4.col-lg-3.mb-3
      ul.nav.flex-column.mb-auto
        li.nav-item
          a.btn.btn-sm.text-nowrap(href="#/help")
            i.bi.bi-house
            span.ms-2 Welcome
        li.nav-item
          a.btn.btn-sm.text-nowrap(href="#/help/how-to-search")
            i.bi.bi-question-circle-fill
            span.ms-2 How to Search
        li.nav-item
          a.btn.btn-sm.text-nowrap(href="#/help/donate")
            i.bi.bi-currency-dollar
            span.ms-2 Donate
        hr
        li.nav-item
          button.btn.btn-sm.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#projects-collapse")
            i.bi.bi-caret-down
            span.ms-2 Projects
          .collapse.ms-3(id="projects-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/cybrex" target="_blank")
                  i.bi.bi-cpu
                  span.ms-2 Cybrex AI
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/geck" target="_blank")
                  i.bi.bi-tools
                  span.ms-2 GECK
              li.nav-item
                a.nav-link.text-secondary(href="#/help/stc-hub-api")
                  i.bi.bi-app
                  span.ms-2 STC Hub API
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/tgbot" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Telegram Bots
              li.nav-item
                a.nav-link.text-secondary(href="https://github.com/nexus-stc/stc/tree/master/web" target="_blank")
                  i.bi.bi-globe
                  span.ms-2 Web STC
        li.nav-item
          button.btn.btn-sm.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#guides-collapse")
            i.bi.bi-caret-down
            span.ms-2 Guides
          .collapse.ms-3(id="guides-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1
              li.nav-item
                a.nav-link.text-secondary(href="#/help/install-ipfs")
                  i.bi.bi-box
                  span.ms-2 Install IPFS
              li.nav-item
                a.nav-link.text-secondary(href="#/help/stc-box")
                  i.bi.bi-book
                  span.ms-2 Create a Compact STC Box for Home or Library Use
              li.nav-item
                a.nav-link.text-secondary(href="#/help/replicate")
                  i.bi.bi-cloud-download
                  span.ms-2 Set Up Your Own Replica
              li.nav-item
                a.nav-link.text-secondary(href="#/help/doomsday")
                  i.bi.bi-radioactive
                  span.ms-2 Doomsday Guide
        li.nav-item
          button.btn.btn-sm.collapsed.text-nowrap(data-bs-toggle="collapse" data-bs-target="#links-collapse")
            i.bi.bi-caret-down
            span.ms-2 Links
          .collapse.ms-3.show(id="links-collapse")
            ul.btn-toggle-nav.list-unstyled.fw-normal.pb-1.small
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://twitter.com/the_superpirate" target="_blank")
                  i.bi.bi-twitter
                  span.ms-2 Twitter
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://kolektiva.social/@the_superpirate" target="_blank")
                  i.bi.bi-mastodon
                  span.ms-2 Mastodon
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/nexus_search" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Telegram Channel
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/+wN8n75kr4nxlMmZi" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Telegram Chat
              li.nav-item
                a.nav-link.text-secondary.text-nowrap(href="https://t.me/science_nexus_bot" target="_blank")
                  i.bi.bi-telegram
                  span.ms-2 Telegram Bot
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
      router-view
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
