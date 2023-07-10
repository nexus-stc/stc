import { createRouter, createWebHashHistory } from "vue-router";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "search",
      component: () => import("../views/SearchView.vue"),
      props: (route) => ({
        q: route.query.q,
        p: Number.parseInt(route.query.p),
        d: route.query.d,
      }),
    },
    {
      path: "/about",
      name: "about",
      component: () => import("../views/AboutView.vue"),
    },
    {
      path: "/bookmarks",
      name: "bookmarks",
      component: () => import("../views/BookmarksView.vue"),
    },
    {
      path: "/donate",
      name: "donate",
      component: () => import("../views/DonateView.vue"),
    },
    {
      path: "/help",
      name: "help",
      component: () => import("../views/HelpView.vue"),
    },
    {
      path: "/replication",
      name: "replication",
      component: () => import("../views/ReplicationView.vue"),
    },
    {
      path: "/dbs",
      name: "dbs",
      component: () => import("../views/DbsView.vue"),
    },
    {
      path: "/:index_alias/:id(.+)",
      name: "document",
      component: () => import("../views/DocumentView.vue"),
      props: true,
    },
  ],
});

export default router;
