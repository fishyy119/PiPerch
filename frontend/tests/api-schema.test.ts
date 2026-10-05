import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import { api } from '@/shared/api/http'

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('API 响应边界', () => {
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
