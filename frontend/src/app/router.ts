import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import ArtworkDetailPage from '@/pages/artworks/ArtworkDetailPage.vue'
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
        { path: 'downloads', component: DownloadPage, meta: { title: '下载工作台' } },
        {
          path: 'gallery',
          component: GalleryPage,
          props: { view: 'artworks' },
          meta: { title: '本地图库', hideTitle: true },
        },
        {
          path: 'gallery/authors',
          component: GalleryPage,
          props: { view: 'authors' },
          meta: { title: '作者', hideTitle: true },
        },
        {
          path: 'gallery/series',
          component: GalleryPage,
          props: { view: 'series' },
          meta: { title: '系列', hideTitle: true },
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
