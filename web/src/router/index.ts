// @ts-nocheck
import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  scrollBehavior (to, from, savedPosition) {
    if (to.path.startsWith("/help") && from.path.startsWith("/help")) {
      return {
        el: '#hrv',
        behavior: 'smooth',
      }
    }
    // always scroll to top
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'search',
      component: async () => await import('../views/SearchView.vue'),
      props: (route) => ({
        q: route.query.q,
        p: Number.parseInt(route.query.p),
        t: route.query.t,
        y: route.query.y
      })
    },
    {
      path: '/bookmarks',
      name: 'bookmarks',
      component: async () => await import('../views/BookmarksView.vue')
    },
    {
      path: '/help',
      name: 'help',
      component: async () => await import('../views/HelpView.vue'),
      children: [
        {
          path: '',
          name: 'intro',
          component: async () => await import('../views/IntroView.vue')
        },
        {
          path: 'doomsday',
          name: 'doomsday',
          component: async () => await import('../views/DoomsdayView.vue')
        },
        {
          path: 'donate',
          name: 'donate',
          component: async () => await import('../views/DonateView.vue')
        },
        {
          path: 'how-to-search',
          name: 'how-to-search',
          component: async () => await import('../views/HowToSearchView.vue')
        },
        {
          path: 'install-ipfs',
          name: 'install-ipfs',
          component: async () => await import('../views/InstallIpfsView.vue')
        },
        {
          path: 'replicate',
          name: 'replicate',
          component: async () => await import('../views/ReplicateView.vue')
        },
        {
          path: 'stc-box',
          name: 'stc-box',
          component: async () => await import('../views/StcBoxView.vue')
        },
        {
          path: 'stc-hub-api',
          name: 'stc-hub-api',
          component: async () => await import('../views/StcHubApiView.vue')
        }
      ]
    },
    {
      path: '/nexus_science/:id(.+)',
      name: 'document',
      component: async () => await import('../views/DocumentView.vue'),
      props: true
    }
  ]
})

export default router
