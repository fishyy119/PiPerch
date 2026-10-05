import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import type { Settings } from '@/features/settings/settings-api'
import { useSettingField } from '@/features/settings/useSettingField'

import { renderComposable } from './composable'

const settingPatches: Record<string, unknown>[] = []

function settingsPayload(pixivCookie = 'PHPSESSID=stored'): Settings {
  return {
    pixivCookie,
    proxyUrl: null,
    libraryRoot: 'C:\\PiPerch\\library',
    downloadConcurrency: 3,
    requestIntervalMs: 500,
    webpEnabled: true,
    webpQuality: 85,
  }
}

const server = setupServer(
  http.get('/api/settings', () => HttpResponse.json(settingsPayload())),
  http.patch('/api/settings', async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>
    settingPatches.push(patch)
    return HttpResponse.json(settingsPayload(String(patch.pixivCookie)))
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => settingPatches.splice(0))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('设置字段保存', () => {
  it('设置项只提交自身字段', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const { result: field, unmount } = renderComposable(
      () => useSettingField('pixivCookie', { label: 'Cookie', initialValue: '' }),
      [[VueQueryPlugin, { queryClient }]],
    )
    try {
      await waitFor(() => expect(field.value.value).toBe('PHPSESSID=stored'))
      field.value.value = 'PHPSESSID=updated'
      field.save()

      await waitFor(() => expect(field.savedValue.value).toBe('PHPSESSID=updated'))
      expect(settingPatches).toEqual([{ pixivCookie: 'PHPSESSID=updated' }])
    } finally {
      unmount()
      queryClient.clear()
    }
  })
})
