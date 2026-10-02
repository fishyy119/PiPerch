import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { vi } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

import ArtworkDetailPage from '@/pages/artworks/ArtworkDetailPage.vue'

function artworkPayload(overrides: Record<string, unknown> = {}) {
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
    tags: [],
    description: '作品说明',
    width: 1000,
    height: 1200,
    media: [{ role: 'page', pageIndex: 0, mimeType: 'image/jpeg', byteSize: 100 }],
    ugoiraFrames: [],
    ...overrides,
  }
}

const server = setupServer(
  http.get('/api/artworks/123', () => HttpResponse.json(artworkPayload())),
  http.get('/api/artworks/123/related', () => HttpResponse.json([])),
)

const LightboxGalleryStub = defineComponent({
  name: 'LightboxGallery',
  props: {
    items: { type: Array, required: true },
  },
  emits: ['change'],
  data: () => ({ openedIndex: null as number | null }),
  methods: {
    open(index = 0) {
      this.openedIndex = index
    },
  },
  template: `
    <div
      data-testid="lightbox-gallery"
      :data-item-count="String(items.length)"
      :data-opened-index="openedIndex === null ? '' : String(openedIndex)"
      :data-first-thumbnail="items[0]?.thumbnailSrc"
    >
      <slot :open="open" />
      <button type="button" @click="$emit('change', 1)">关闭并停在第二页</button>
    </div>
  `,
})

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  vi.restoreAllMocks()
})
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

    expect(await screen.findByRole('heading', { name: '测试作品' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '相关作品' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Pixiv 主页/u })).toHaveAttribute(
      'href',
      'https://www.pixiv.net/users/456',
    )

    await user.click(screen.getByRole('button', { name: /测试作者/u }))

    await waitFor(() => {
      expect(router.currentRoute.value.path).toBe('/gallery')
      expect(router.currentRoute.value.query.authorId).toBe('456')
    })
  })

  it('从整个主图展示区打开当前页，并同步 Lightbox 内的翻页结果', async () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(200)
    server.use(
      http.get('/api/artworks/123', () =>
        HttpResponse.json(
          artworkPayload({
            artworkType: 'manga',
            seriesId: null,
            seriesTitle: null,
            pageCount: 3,
            media: [
              { role: 'page', pageIndex: 0, mimeType: 'image/jpeg', byteSize: 100 },
              { role: 'page', pageIndex: 1, mimeType: 'image/jpeg', byteSize: 100 },
              { role: 'page', pageIndex: 2, mimeType: 'image/jpeg', byteSize: 100 },
            ],
          }),
        ),
      ),
    )
    const user = userEvent.setup()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/artworks/:artworkId', component: ArtworkDetailPage }],
    })
    await router.push('/artworks/123')
    await router.isReady()

    render(
      { components: { RouterView }, template: '<RouterView />' },
      {
        global: {
          plugins: [router, [VueQueryPlugin, { queryClient: new QueryClient() }]],
          stubs: { LightboxGallery: LightboxGalleryStub },
        },
      },
    )

    const previewTrigger = await screen.findByRole('button', {
      name: '测试作品',
    })

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: '3' })).not.toBeInTheDocument()
    })
    await user.click(await screen.findByRole('button', { name: /展开全部/u }))
    await user.click(screen.getByRole('button', { name: '3' }))
    await user.click(previewTrigger)

    expect(screen.getByTestId('lightbox-gallery')).toHaveAttribute('data-item-count', '3')
    expect(screen.getByTestId('lightbox-gallery')).toHaveAttribute('data-opened-index', '2')
    expect(screen.getByTestId('lightbox-gallery')).toHaveAttribute(
      'data-first-thumbnail',
      '/api/artworks/123/pages/0/thumbnail',
    )

    await user.click(screen.getByRole('button', { name: '关闭并停在第二页' }))
    expect(screen.getByText(/第 2 \/ 3 页/u)).toBeInTheDocument()
  })
})
