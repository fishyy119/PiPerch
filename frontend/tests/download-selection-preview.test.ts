import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'

import type { DiscoveryItem } from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DownloadJobsSidebar from '@/pages/downloads/DownloadJobsSidebar.vue'

function candidate(artworkId: number): DiscoveryItem {
  return {
    artworkId,
    title: `作品 ${String(artworkId)}`,
    authorName: '测试作者',
    artworkType: 'illust',
    pageCount: 1,
    xRestrict: 0,
    isAi: false,
    thumbnailUrl: `/api/pixiv-images?url=${encodeURIComponent(
      `https://i.pximg.net/${String(artworkId)}.jpg`,
    )}`,
    inLibrary: false,
  }
}

const server = setupServer(
  http.get('/api/download-jobs', () =>
    HttpResponse.json({ items: [], page: 0, size: 100, totalElements: 0, totalPages: 0 }),
  ),
  http.post('/api/download-jobs', () => HttpResponse.json({ jobId: 'job-preview' })),
)

class EventSourceMock {
  addEventListener() {
    return undefined
  }

  close() {
    return undefined
  }
}

let resizeObserverCallback: ResizeObserverCallback | undefined
let resizeObserverTarget: Element | undefined

class ResizeObserverMock {
  constructor(callback: ResizeObserverCallback) {
    resizeObserverCallback = callback
  }

  observe(target: Element) {
    resizeObserverTarget = target
  }

  disconnect() {
    resizeObserverTarget = undefined
  }
}

function resizePreview(width: number) {
  if (resizeObserverCallback === undefined || resizeObserverTarget === undefined) {
    throw new Error('预览网格尚未开始监听尺寸。')
  }
  resizeObserverCallback(
    [{ target: resizeObserverTarget, contentRect: { width } } as ResizeObserverEntry],
    {} as ResizeObserver,
  )
}

function setupSelection() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const selection = useDownloadSelection()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const rendered = render(DownloadJobsSidebar, {
    props: { sourceLabel: '作品' },
    global: { plugins: [pinia, [VueQueryPlugin, { queryClient }]] },
  })
  return { ...rendered, selection }
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})
beforeEach(() => {
  resizeObserverCallback = undefined
  resizeObserverTarget = undefined
  vi.stubGlobal('EventSource', EventSourceMock)
  vi.stubGlobal('ResizeObserver', ResizeObserverMock)
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
})
afterAll(() => {
  server.close()
  vi.unstubAllGlobals()
})

describe('下载队列预览', () => {
  it('默认收起并复用缓存，以四列展示前 16 项且允许移除和提交', async () => {
    const user = userEvent.setup()
    const { container, selection } = setupSelection()
    selection.addAll(Array.from({ length: 17 }, (_, index) => candidate(index + 1)))

    expect(await screen.findByText('已选择 17 项')).toBeInTheDocument()
    expect(container.querySelectorAll('img')).toHaveLength(0)

    await user.click(screen.getByRole('button', { name: '展开预览' }))
    resizePreview(342)

    await waitFor(() => expect(container.querySelectorAll('img')).toHaveLength(16))
    expect(container.querySelector('.grid')).toHaveClass(
      'grid-cols-[repeat(auto-fill,79.5px)]',
      'justify-between',
    )
    expect(screen.getByText('另有 1 项未展示')).toBeInTheDocument()
    expect(screen.queryByTitle('作品 17')).not.toBeInTheDocument()

    await user.click(screen.getByTitle('从队列移除作品 1'))

    expect(screen.getByText('已选择 16 项')).toBeInTheDocument()
    expect(screen.getByTitle('作品 17')).toBeInTheDocument()
    expect(screen.queryByText(/项未展示/u)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '创建下载任务' }))
    await waitFor(() => expect(screen.getByText('已选择 0 项')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: '收起预览' })).not.toBeInTheDocument()
    expect(container.querySelector('.grid')).not.toBeInTheDocument()
  })

  it('保持缩略图宽度和四行高度，并随容器增宽增加列数', async () => {
    const user = userEvent.setup()
    const { container, selection } = setupSelection()
    selection.addAll(Array.from({ length: 25 }, (_, index) => candidate(index + 1)))

    await user.click(await screen.findByRole('button', { name: '展开预览' }))
    resizePreview(342)
    await waitFor(() => expect(container.querySelectorAll('img')).toHaveLength(16))
    expect(screen.getByText('另有 9 项未展示')).toBeInTheDocument()

    resizePreview(429.5)
    await waitFor(() => expect(container.querySelectorAll('img')).toHaveLength(20))
    expect(screen.getByText('另有 5 项未展示')).toBeInTheDocument()

    resizePreview(517)
    await waitFor(() => expect(container.querySelectorAll('img')).toHaveLength(24))
    expect(screen.getByText('另有 1 项未展示')).toBeInTheDocument()
  })

  it('不足一行时仍保留完整网格列轨道', async () => {
    const user = userEvent.setup()
    const { container, selection } = setupSelection()
    selection.addAll([candidate(1), candidate(2), candidate(3)])

    await user.click(await screen.findByRole('button', { name: '展开预览' }))
    resizePreview(517)

    const grid = container.querySelector('.grid')
    await waitFor(() => expect(grid?.children).toHaveLength(3))
    expect(grid).toHaveClass('grid-cols-[repeat(auto-fill,79.5px)]', 'justify-between')
  })

  it('展开后只加载缺失的前 16 项，失败可重试并在移除后补位', async () => {
    const user = userEvent.setup()
    const requests: string[][] = []
    let requestCount = 0
    server.use(
      http.post('/api/discovery', async ({ request }) => {
        const body = (await request.json()) as { inputs: string[] }
        requests.push(body.inputs)
        requestCount += 1
        if (requestCount === 1) {
          return HttpResponse.json(
            { error: { code: 'preview_failed', message: '预览暂不可用。' } },
            { status: 503 },
          )
        }
        return HttpResponse.json({
          items: body.inputs.map((input) => candidate(Number(input))),
          page: 0,
          nextPage: null,
        })
      }),
    )

    const { container, selection } = setupSelection()
    selection.addIds(Array.from({ length: 17 }, (_, index) => index + 1))

    expect(await screen.findByText('已选择 17 项')).toBeInTheDocument()
    expect(requests).toEqual([])

    await user.click(screen.getByRole('button', { name: '展开预览' }))
    resizePreview(342)
    expect(await screen.findByText('预览暂不可用。')).toBeInTheDocument()
    expect(requests).toEqual([Array.from({ length: 16 }, (_, index) => String(index + 1))])
    expect(container.querySelectorAll('.grid > div')).toHaveLength(16)

    await user.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => expect(container.querySelectorAll('img')).toHaveLength(16))
    expect(requests).toHaveLength(2)

    await user.click(screen.getByTitle('从队列移除作品 1'))
    await waitFor(() => expect(requests).toHaveLength(3))
    expect(requests[2]).toEqual(['17'])
    expect(await screen.findByTitle('作品 17')).toBeInTheDocument()
  })
})
