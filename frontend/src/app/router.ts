import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import ArtworkDetailPage from '@/pages/artworks/ArtworkDetailPage.vue'
import DiscoverPage from '@/pages/discover/DiscoverPage.vue'
import DownloadPage from '@/pages/downloads/DownloadPage.vue'
import GalleryPage from '@/pages/gallery/GalleryPage.vue'
import SettingsPage from '@/pages/settings/SettingsPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/gallery' },
        { path: 'discover', component: DiscoverPage, meta: { title: '发现', hideTitle: true } },
        {
          path: 'downloads',
          component: DownloadPage,
          meta: { title: '下载工作台', hideTitle: true },
        },
        {
          path: 'gallery',
          component: GalleryPage,
          meta: { title: '本地图库', hideTitle: true },
        },
        {
          path: 'artworks/:artworkId(\\d+)',
          component: ArtworkDetailPage,
          meta: { title: '作品详情' },
        },
        {
          path: 'settings',
          component: SettingsPage,
          meta: { title: '设置', flushContent: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/gallery' },
  ],
})
