import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'

import { useDownloadSelection } from '@/features/downloads/download-selection'
import DownloadJobsSidebar from '@/pages/downloads/DownloadJobsSidebar.vue'

interface DownloadRequestBody {
  artworkIds: number[]
  sourceLabel: string
}

const submittedRequests: DownloadRequestBody[] = []

const server = setupServer(
  http.get('/api/download-jobs', () =>
    HttpResponse.json({ items: [], page: 0, size: 100, totalElements: 0, totalPages: 0 }),
  ),
  http.post('/api/download-jobs', async ({ request }) => {
    submittedRequests.push((await request.json()) as DownloadRequestBody)
    if (submittedRequests.length === 1) return HttpResponse.json({ jobId: 'job-1' })
    return HttpResponse.json(
      { error: { code: 'submission_failed', message: '暂时无法创建任务。' } },
      { status: 503 },
    )
  }),
)

class EventSourceMock {
  addEventListener() {
    return undefined
  }

  close() {
    return undefined
  }
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  submittedRequests.splice(0)
  vi.stubGlobal('EventSource', EventSourceMock)
})
afterEach(() => server.resetHandlers())
afterAll(() => {
  server.close()
  vi.unstubAllGlobals()
})

describe('下载任务提交', () => {
  it('分批提交失败时只移除已经提交的作品', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const selection = useDownloadSelection()
    selection.addIds(Array.from({ length: 1001 }, (_, index) => index + 1))
    const user = userEvent.setup()

    render(DownloadJobsSidebar, {
      props: { sourceLabel: '作品' },
      global: {
        plugins: [
          pinia,
          [
            VueQueryPlugin,
            {
              queryClient: new QueryClient({
                defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
              }),
            },
          ],
        ],
      },
    })

    await user.click(screen.getByRole('button', { name: '创建下载任务' }))

    await waitFor(() => expect(submittedRequests).toHaveLength(2))
    expect(submittedRequests[0]?.artworkIds).toHaveLength(1000)
    expect(submittedRequests[0]?.artworkIds[0]).toBe(1)
    expect(submittedRequests[0]?.artworkIds.at(-1)).toBe(1000)
    expect(submittedRequests[1]?.artworkIds).toEqual([1001])
    await waitFor(() => expect(selection.selectedIds).toEqual([1001]))
  })
})
