import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

import ArtworkDetailPage from '@/pages/artworks/ArtworkDetailPage.vue'

function artworkPayload() {
  return {
    artworkId: 123,
    title: '测试作品',
    artworkType: 'illust',
    authorId: 456,
    authorName: '测试作者',
    seriesId: 789,
    seriesTitle: '测试系列',
    pageCount: 1,
    xRestrict: 0,
    isAi: false,
    publishedAt: '2026-09-28T00:00:00Z',
    downloadedAt: '2026-09-28T01:00:00Z',
    isFavorite: false,
    groupIds: [],
    tags: [],
    description: '作品说明',
    width: 1000,
    height: 1200,
    media: [{ role: 'page', pageIndex: 0, mimeType: 'image/jpeg', byteSize: 100 }],
    ugoiraFrames: [],
  }
}

const server = setupServer(
  http.get('/api/artworks/123', () => HttpResponse.json(artworkPayload())),
  http.get('/api/artworks/123/related', () => HttpResponse.json([])),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('作品详情页', () => {
  it('显示作者信息并通过作者卡应用图库筛选', async () => {
    const user = userEvent.setup()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/artworks/:artworkId', component: ArtworkDetailPage },
        { path: '/gallery', component: { template: '<div>图库</div>' } },
      ],
    })
    await router.push('/artworks/123')
    await router.isReady()

    render(
      { components: { RouterView }, template: '<RouterView />' },
      {
        global: {
          plugins: [router, [VueQueryPlugin, { queryClient: new QueryClient() }]],
        },
      },
    )

    await user.click(await screen.findByRole('button', { name: /测试作者/u }))

    await waitFor(() => {
      expect(router.currentRoute.value.path).toBe('/gallery')
      expect(router.currentRoute.value.query.authorId).toBe('456')
    })
  })
})
