<template lang="pug">
div.d-flex.flex-column.min-vh-100.w-100
  header
    nav.navbar.navbar-expand
      .container-fluid
        router-link.ms-2.navbar-brand(to="/")
          img.favicon-inversion-filter(src="/favicon-black.svg" alt="" width="48" height="48")
        .navbar-nav.me-auto
        .navbar-nav
          router-link.nav-link(to="/bookmarks" data-bs-toggle="tooltip" data-bs-placement="top" title="Bookmarks")
            div.text-center
              i.bi.bi-bookmark
          router-link.nav-link(to="/help" data-bs-toggle="tooltip" data-bs-placement="top" title="help")
            div.text-center
              i.bi.bi-question-circle-fill
  .mb-3
    router-view
  footer.footer.mt-auto.text-end.small.mb-3
    .container.small
      div {{ get_label ("stamp") }}
      a(href="https://github.com/nexus-stc/stc/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=") Report a bug
      span &nbsp;|&nbsp;
      a(href="/#/help") Help
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

export default defineComponent({
  name: 'App',
  components: {
    RouterLink,
    RouterView
  }
})
</script>
<style scoped lang="scss">
.nav-link div {
  font-size: 75%;
}
.nav-link i {
  font-size: 200%;
}
.logo {
  background: linear-gradient(90deg, #644494, #FE9609);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
@media (prefers-color-scheme: dark) {
  .logo {
    background: linear-gradient(90deg, #FE9609, #644494);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}
</style>
