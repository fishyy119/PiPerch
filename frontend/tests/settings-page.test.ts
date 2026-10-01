import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import SettingsPage from '@/pages/settings/SettingsPage.vue'

const settingPatches: Record<string, unknown>[] = []

function settingsPayload(pixivCookie = 'PHPSESSID=stored') {
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

describe('设置页', () => {
  it('设置项只提交自身字段', async () => {
    const user = userEvent.setup()
    render(SettingsPage, {
      global: {
        plugins: [
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

    const input = await screen.findByLabelText('Cookie')
    await waitFor(() => expect(input).toHaveValue('PHPSESSID=stored'))
    await user.clear(input)
    await user.type(input, 'PHPSESSID=updated')
    await user.tab()

    await waitFor(() => expect(settingPatches).toEqual([{ pixivCookie: 'PHPSESSID=updated' }]))
  })
})
