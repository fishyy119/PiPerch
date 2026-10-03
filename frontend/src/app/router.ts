import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/gallery' },
        {
          path: 'discover',
          component: () => import('@/pages/discover/DiscoverPage.vue'),
          meta: { title: '发现', hideTitle: true },
        },
        {
          path: 'downloads',
          component: () => import('@/pages/downloads/DownloadPage.vue'),
          meta: { title: '下载工作台', hideTitle: true },
        },
        {
          path: 'gallery',
          component: () => import('@/pages/gallery/GalleryPage.vue'),
          meta: { title: '本地图库', hideTitle: true },
        },
        {
          path: 'favorites',
          component: () => import('@/pages/favorites/FavoritesPage.vue'),
          meta: { title: '收藏' },
        },
        {
          path: 'artworks/:artworkId(\\d+)',
          component: () => import('@/pages/artworks/ArtworkDetailPage.vue'),
          meta: { title: '作品详情' },
        },
        {
          path: 'settings',
          component: () => import('@/pages/settings/SettingsPage.vue'),
          meta: { title: '设置', flushContent: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/gallery' },
  ],
})
