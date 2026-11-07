import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createPinia, setActivePinia } from 'pinia'

import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadSubmissionStore } from '@/features/downloads/download-submission'

import { renderComposable } from './composable'

interface DownloadRequestBody {
  source: 'pixiv' | 'fanbox'
  artworkIds: number[]
  authorIds?: Record<string, number>
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
  it('分来源分批提交失败后，仅重试尚未提交的完整引用', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const selection = useDownloadSelection()
    selection.add(
      Array.from({ length: 1001 }, (_, index) => ({ source: 'pixiv', remoteId: index + 1 })),
    )
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
        submittedReferences: submittedIds.map((remoteId) => ({ source: 'pixiv', remoteId })),
        remainingCount: 1,
        failedError: { code: 'submission_failed', status: 503 },
      })
      expect(selection.selectedReferences).toEqual([{ source: 'pixiv', remoteId: 1001 }])
      selection.add([{ source: 'fanbox', remoteId: 1001, authorId: 42 }])
      server.use(
        http.post('/api/download-jobs', async ({ request }) => {
          submittedRequests.push((await request.json()) as DownloadRequestBody)
          return HttpResponse.json({ jobId: 'retry-job' })
        }),
      )
      await submission.submit('FANBOX')
      expect(submittedRequests.slice(2)).toMatchObject([
        { source: 'pixiv', artworkIds: [1001] },
        { source: 'fanbox', artworkIds: [1001], authorIds: { '1001': 42 } },
      ])
      expect(selection.selectedReferences).toEqual([])
    } finally {
      unmount()
      queryClient.clear()
    }
  })
})
