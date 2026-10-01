import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia } from 'pinia'

import BookmarkSourceTab from '@/pages/downloads/sources/BookmarkSourceTab.vue'

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
  http.get('/api/discovery/bookmark-folders', () =>
    HttpResponse.json({
      items: [
        { visibility: 'public', tag: '风景', kind: 'tag', name: '风景', itemCount: 49 },
        { visibility: 'private', tag: '私藏', kind: 'tag', name: '私藏', itemCount: 48 },
      ],
    }),
  ),
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
    const user = userEvent.setup()
    render(BookmarkSourceTab, {
      global: {
        plugins: [createPinia(), [VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    await user.click(await screen.findByRole('button', { name: /风景/u }))
    await user.click(screen.getByRole('button', { name: /私藏/u }))
    await user.click(screen.getByRole('button', { name: '确认并预览' }))
    expect(await screen.findByText('公开作品 1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '下一页' }))
    expect(await screen.findByText('公开补位作品')).toBeInTheDocument()
    expect(screen.queryByText('跨标签重复作品')).not.toBeInTheDocument()
    await waitFor(() =>
      expect(discoveryRequests).toEqual([
        { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 0 },
        { sourceType: 'bookmark', folder: { visibility: 'private', tag: '私藏' }, page: 0 },
        { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 1 },
      ]),
    )
  })
})
