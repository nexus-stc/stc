<template lang="pug">
div.d-flex.flex-column.min-vh-100.w-100
  header
    nav.navbar.navbar-expand
      .container-fluid
        router-link.navbar-brand(to="/")
          img.favicon-inversion-filter(src="/favicon-black.svg" alt="" width="48" height="48")
        .navbar-nav.me-auto
        .navbar-nav
          router-link.nav-link(to="/bookmarks" data-bs-toggle="tooltip" data-bs-placement="top" title="Bookmarks")
            div.text-center
              i.bi.bi-bookmark
          router-link.nav-link(to="/help" data-bs-toggle="tooltip" data-bs-placement="top" title="help")
            div.text-center
              i.bi.bi-question-circle-fill
  .col-md-7.offset-md-2.mb-5.mt-1
    router-view.container
  footer.footer.mt-auto.text-end.small.mb-3
    .container.small Standard Template Construct, version 27 Jun 23
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { RouterLink, RouterView } from "vue-router";

export default defineComponent({
  name: "App",
  components: {
    RouterLink,
    RouterView,
  },
});
</script>
<style scoped lang="scss">
.nav-link div {
  font-size: 75%;
}
.nav-link i {
  font-size: 200%;
}
</style>
