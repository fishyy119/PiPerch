import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { ZodError } from 'zod'

import { discover } from '@/features/downloads/download-api'
import { api } from '@/shared/api/http'

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('API 响应边界', () => {
  it('拒绝不符合来源预览契约的响应', async () => {
    server.use(
      http.post('/api/discovery', () =>
        HttpResponse.json({
          items: [
            {
              artworkId: 123,
              title: '测试作品',
              artworkType: 'manga',
              pageCount: 2,
              xRestrict: 0,
              isAi: false,
              thumbnailUrl: null,
              inLibrary: true,
            },
          ],
          page: 0,
          nextPage: 1,
        }),
      ),
    )

    await expect(
      discover({ sourceType: 'artwork', inputs: ['123'], page: 0 }),
    ).rejects.toBeInstanceOf(ZodError)
  })

  it('保留后端稳定错误码、消息和状态码', async () => {
    server.use(
      http.get('/api/failure', () =>
        HttpResponse.json(
          { error: { code: 'cookie_required', message: '请先配置 Pixiv Cookie。' } },
          { status: 409 },
        ),
      ),
    )

    await expect(api.get('/api/failure')).rejects.toMatchObject({
      code: 'cookie_required',
      message: '请先配置 Pixiv Cookie。',
      status: 409,
    })
  })
})
