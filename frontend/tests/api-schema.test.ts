import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import {
  discover,
  listFollowedUsers,
  listSelectableUserArtworkIds,
} from '@/features/downloads/download-api'
import { listArtworks } from '@/features/gallery/gallery-api'
import { api } from '@/shared/api/http'

const server = setupServer()

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('API 响应边界', () => {
  it('使用 Zod 校验来源预览响应', async () => {
    server.use(
      http.post('/api/discovery', () =>
        HttpResponse.json({
          items: [
            {
              artworkId: 123,
              title: '测试作品',
              authorName: '作者',
              artworkType: 'manga',
              pageCount: 2,
              xRestrict: 0,
              isAi: false,
              thumbnailUrl: '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2Fexample.jpg',
              inLibrary: true,
            },
          ],
          page: 0,
          nextPage: 1,
        }),
      ),
    )

    const result = await discover({ sourceType: 'artwork', inputs: ['123'], page: 0 })
    expect(result.items[0]?.artworkId).toBe(123)
    expect(result.items[0]?.inLibrary).toBe(true)
    expect(result.nextPage).toBe(1)
  })

  it('保留后端稳定错误码与中文消息', async () => {
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

  it('读取作者全部作品 ID', async () => {
    server.use(
      http.get('/api/discovery/users/42/selectable-artwork-ids', () =>
        HttpResponse.json({ artworkIds: [103, 102, 101] }),
      ),
    )

    await expect(listSelectableUserArtworkIds(42)).resolves.toEqual([103, 102, 101])
  })

  it('读取当前账号关注的作者', async () => {
    server.use(
      http.get('/api/discovery/followed-users', () =>
        HttpResponse.json({
          items: [
            {
              userId: 42,
              name: '测试作者',
              avatarUrl: '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2Favatar.jpg',
            },
          ],
        }),
      ),
    )

    await expect(listFollowedUsers()).resolves.toEqual([
      {
        userId: 42,
        name: '测试作者',
        avatarUrl: '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2Favatar.jpg',
      },
    ])
  })

  it('图库请求携带单页作品数量', async () => {
    server.use(
      http.get('/api/artworks', ({ request }) => {
        expect(new URL(request.url).searchParams.get('size')).toBe('48')
        return HttpResponse.json({
          items: [],
          page: 0,
          size: 48,
          totalElements: 0,
          totalPages: 0,
        })
      }),
    )

    const result = await listArtworks({
      page: 0,
      size: 48,
      search: '',
      tagIds: [],
      rating: 'all',
      ai: 'all',
      sort: 'downloadedAt',
      order: 'desc',
    })

    expect(result.size).toBe(48)
  })
})
