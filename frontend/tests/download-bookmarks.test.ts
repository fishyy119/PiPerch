import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia, setActivePinia } from 'pinia'
import { effectScope } from 'vue'

import { useBookmarkPreview } from '@/features/downloads/useBookmarkPreview'

import { discoveryItem } from './fixtures'

interface BookmarkRequestBody {
  sourceType: 'bookmark'
  folder: { visibility: 'public' | 'private'; tag: string | null }
  page: number
}

const discoveryRequests: BookmarkRequestBody[] = []
const publicFirstPage = Array.from({ length: 48 }, (_, index) =>
  discoveryItem(1001 + index, { title: `公开作品 ${String(index + 1)}` }),
)
const privateFirstPage = [
  discoveryItem(1001, { title: '跨标签重复作品' }),
  ...Array.from({ length: 47 }, (_, index) =>
    discoveryItem(2001 + index, { title: `非公开作品 ${String(index + 1)}` }),
  ),
]

const server = setupServer(
  http.post('/api/discovery', async ({ request }) => {
    const body = (await request.json()) as BookmarkRequestBody
    discoveryRequests.push(body)
    if (body.folder.visibility === 'public' && body.page === 0) {
      return HttpResponse.json({ items: publicFirstPage, page: 0, nextPage: 1 })
    }
    if (body.folder.visibility === 'private') {
      return HttpResponse.json({ items: privateFirstPage, page: 0, nextPage: null })
    }
    return HttpResponse.json({
      items: [discoveryItem(3001, { title: '公开补位作品' })],
      page: 1,
      nextPage: null,
    })
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => discoveryRequests.splice(0))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('收藏下载来源', () => {
  it('跨收藏夹分页时轮询来源并去除重复作品', async () => {
    setActivePinia(createPinia())
    const scope = effectScope()
    try {
      await scope.run(async () => {
        const preview = useBookmarkPreview()
        preview.reset([
          { visibility: 'public', tag: '风景' },
          { visibility: 'private', tag: '私藏' },
        ])
        await preview.loadPage(0)
        expect(preview.candidates.value.map((item) => item.artworkId)).toEqual(
          publicFirstPage.map((item) => item.artworkId),
        )
        expect(preview.nextPage.value).toBe(1)

        await preview.loadPage(1)
        expect(preview.candidates.value.map((item) => item.artworkId)).toEqual([
          ...privateFirstPage.slice(1).map((item) => item.artworkId),
          3001,
        ])
        expect(preview.page.value).toBe(1)
        expect(preview.nextPage.value).toBeNull()
        expect(discoveryRequests).toEqual([
          { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 0 },
          { sourceType: 'bookmark', folder: { visibility: 'private', tag: '私藏' }, page: 0 },
          { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 1 },
        ])
      })
    } finally {
      scope.stop()
    }
  })
})
