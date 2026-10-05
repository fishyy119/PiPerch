import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia, setActivePinia } from 'pinia'

import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadSubmissionStore } from '@/features/downloads/download-submission'

import { renderComposable } from './composable'

interface DownloadRequestBody {
  artworkIds: number[]
  sourceLabel: string
}

const submittedRequests: DownloadRequestBody[] = []

const server = setupServer(
  http.post('/api/download-jobs', async ({ request }) => {
    submittedRequests.push((await request.json()) as DownloadRequestBody)
    if (submittedRequests.length === 1) return HttpResponse.json({ jobId: 'job-1' })
    return HttpResponse.json(
      { error: { code: 'submission_failed', message: '暂时无法创建任务。' } },
      { status: 503 },
    )
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => submittedRequests.splice(0))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('下载任务提交', () => {
  it('分批提交失败时只移除已经提交的作品', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const selection = useDownloadSelection()
    selection.addIds(Array.from({ length: 1001 }, (_, index) => index + 1))
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const { result: submission, unmount } = renderComposable(useDownloadSubmissionStore, [
      pinia,
      [VueQueryPlugin, { queryClient }],
    ])
    try {
      const result = await submission.submit('作品')

      const submittedIds = Array.from({ length: 1000 }, (_, index) => index + 1)
      expect(submittedRequests.map((request) => request.artworkIds)).toEqual([submittedIds, [1001]])
      expect(result).toMatchObject({
        createdJobCount: 1,
        submittedArtworkIds: submittedIds,
        remainingCount: 1,
        failedError: { code: 'submission_failed', status: 503 },
      })
      expect(selection.selectedIds).toEqual([1001])
    } finally {
      unmount()
      queryClient.clear()
    }
  })
})
