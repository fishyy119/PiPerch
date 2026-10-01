import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia } from 'pinia'
import { vi } from 'vitest'

import type { DiscoveryItem } from '@/features/downloads/download-api'
import DownloadPage from '@/pages/downloads/DownloadPage.vue'

interface BookmarkRequestBody {
  sourceType: 'bookmark'
  folder: { visibility: 'public' | 'private'; tag: string | null }
  page: number
}

const discoveryRequests: BookmarkRequestBody[] = []
let bookmarkFolderRequests = 0

function candidate(artworkId: number, title: string): DiscoveryItem {
  return {
    artworkId,
    title,
    authorName: '测试作者',
    artworkType: 'illust',
    pageCount: 1,
    xRestrict: 0,
    isAi: false,
    thumbnailUrl: null,
    inLibrary: false,
  }
}

const publicFirstPage = Array.from({ length: 48 }, (_, index) =>
  candidate(1001 + index, `公开作品 ${String(index + 1)}`),
)
const privateFirstPage = [
  candidate(1001, '跨标签重复作品'),
  ...Array.from({ length: 47 }, (_, index) =>
    candidate(2001 + index, `非公开作品 ${String(index + 1)}`),
  ),
]

const server = setupServer(
  http.get('/api/download-jobs', () =>
    HttpResponse.json({ items: [], page: 0, size: 100, totalElements: 0, totalPages: 0 }),
  ),
  http.get('/api/discovery/bookmark-folders', () => {
    bookmarkFolderRequests += 1
    return HttpResponse.json({
      items: [
        {
          visibility: 'public',
          tag: '风景',
          kind: 'tag',
          name: '风景',
          itemCount: 49,
        },
        {
          visibility: 'private',
          tag: '私藏',
          kind: 'tag',
          name: '私藏',
          itemCount: 48,
        },
      ],
    })
  }),
  http.post('/api/discovery', async ({ request }) => {
    const body = (await request.json()) as BookmarkRequestBody
    discoveryRequests.push(body)
    if (body.folder.visibility === 'public' && body.page === 0) {
      return HttpResponse.json({ items: publicFirstPage, page: 0, nextPage: 1 })
    }
    if (body.folder.visibility === 'private') {
      return HttpResponse.json({ items: privateFirstPage, page: 0, nextPage: null })
    }
    return HttpResponse.json({ items: [candidate(3001, '公开补位作品')], page: 1, nextPage: null })
  }),
  http.post('/api/discovery/bookmarks/selectable-artwork-ids', () =>
    HttpResponse.json({ artworkIds: [5001, 5002] }),
  ),
)

class EventSourceMock {
  addEventListener() {
    return undefined
  }

  close() {
    return undefined
  }
}

beforeAll(() => {
  vi.stubGlobal('EventSource', EventSourceMock)
  server.listen({ onUnhandledRequest: 'error' })
})
beforeEach(() => {
  discoveryRequests.length = 0
  bookmarkFolderRequests = 0
})
afterEach(() => server.resetHandlers())
afterAll(() => {
  server.close()
  vi.unstubAllGlobals()
})

describe('收藏下载来源', () => {
  it('将当前作品的页进度计入任务进度条', async () => {
    server.use(
      http.get('/api/download-jobs', () =>
        HttpResponse.json({
          items: [
            {
              jobId: 'job-progress',
              sourceLabel: '收藏来源',
              state: 'running',
              createdAt: '2026-10-01T00:00:00Z',
              startedAt: '2026-10-01T00:00:01Z',
              finishedAt: null,
              errorSummary: null,
              counts: {
                queued: 7,
                running: 1,
                skipped: 0,
                succeeded: 2,
                failed: 0,
                cancelled: 0,
              },
              progress: {
                currentArtworkId: 123456,
                completedPages: 37,
                totalPages: 120,
                phase: 'downloading',
              },
            },
          ],
          page: 0,
          size: 100,
          totalElements: 1,
          totalPages: 1,
        }),
      ),
    )
    const { container } = render(DownloadPage, {
      global: {
        plugins: [createPinia(), [VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    expect(await screen.findByText('作品 123456 · 37 / 120 页')).toBeInTheDocument()
    const progressBar = container.querySelector('.h-full.bg-primary.transition-all')
    expect(progressBar).toHaveStyle({ width: `${String(((2 + 37 / 120) / 10) * 100)}%` })
  })

  it('稳定缓存收藏标签，并只在主动刷新时重新获取', async () => {
    const user = userEvent.setup()
    render(DownloadPage, {
      global: {
        plugins: [createPinia(), [VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    await user.click(screen.getByRole('button', { name: '收藏' }))
    expect(await screen.findByRole('button', { name: /风景/u })).toBeInTheDocument()
    expect(bookmarkFolderRequests).toBe(1)

    await user.click(screen.getByRole('button', { name: '用户' }))
    await user.click(screen.getByRole('button', { name: '收藏' }))
    expect(await screen.findByRole('button', { name: /风景/u })).toBeInTheDocument()
    expect(bookmarkFolderRequests).toBe(1)

    const confirmButton = screen.getByRole('button', { name: '确认并预览' })
    const actions = confirmButton.parentElement
    if (!actions) throw new Error('缺少收藏标签操作栏。')
    await user.click(within(actions).getByRole('button', { name: '刷新' }))
    await waitFor(() => expect(bookmarkFolderRequests).toBe(2))
  })

  it('位于用户与系列之间，并按收藏夹轮询懒加载、去重和选择全部', async () => {
    const user = userEvent.setup()
    render(DownloadPage, {
      global: {
        plugins: [createPinia(), [VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    const sourceTabs = ['作品', '用户', '收藏', '系列'].map((name) =>
      screen.getByRole('button', { name }),
    )
    expect(sourceTabs.map((button) => button.textContent)).toEqual(['作品', '用户', '收藏', '系列'])

    const bookmarkTab = sourceTabs[2]
    if (!bookmarkTab) throw new Error('缺少收藏来源标签。')
    await user.click(bookmarkTab)
    await user.click(await screen.findByRole('button', { name: /风景/u }))
    await user.click(screen.getByRole('button', { name: /私藏/u }))
    await user.click(screen.getByRole('button', { name: '确认并预览' }))

    expect(await screen.findByText('公开作品 1')).toBeInTheDocument()
    expect(discoveryRequests).toEqual([
      { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 0 },
    ])
    expect(screen.getByRole('button', { name: '更换收藏夹' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '下一页' }))
    expect(await screen.findByText('公开补位作品')).toBeInTheDocument()
    await waitFor(() =>
      expect(discoveryRequests).toEqual([
        { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 0 },
        { sourceType: 'bookmark', folder: { visibility: 'private', tag: '私藏' }, page: 0 },
        { sourceType: 'bookmark', folder: { visibility: 'public', tag: '风景' }, page: 1 },
      ]),
    )

    await user.click(screen.getByRole('button', { name: '选择全部' }))
    expect(await screen.findByRole('button', { name: '取消全部（2）' })).toBeInTheDocument()
    expect(screen.getByText('已选择 2 项')).toBeInTheDocument()
  })
})
