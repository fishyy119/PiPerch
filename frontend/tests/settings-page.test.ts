import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import SettingsPage from '@/pages/settings/SettingsPage.vue'

let pixivCookie = 'PHPSESSID=stored'
let webpEnabled = true
let webpQuality = 85

const server = setupServer(
  http.get('/api/settings', () =>
    HttpResponse.json({
      pixivCookie,
      proxyUrl: null,
      libraryRoot: 'C:\\PiPerch\\library',
      downloadConcurrency: 3,
      requestIntervalMs: 500,
      webpEnabled,
      webpQuality,
    }),
  ),
  http.put('/api/settings', async ({ request }) => {
    const settings = (await request.json()) as {
      pixivCookie: string | null
      proxyUrl: string | null
      libraryRoot: string
      downloadConcurrency: number
      requestIntervalMs: number
      webpEnabled: boolean
      webpQuality: number
    }
    pixivCookie = settings.pixivCookie ?? ''
    webpEnabled = settings.webpEnabled
    webpQuality = settings.webpQuality
    return HttpResponse.json(settings)
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  pixivCookie = 'PHPSESSID=stored'
  webpEnabled = true
  webpQuality = 85
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('设置页', () => {
  it('回显 Cookie，并通过统一设置提交保存', async () => {
    const user = userEvent.setup()
    render(SettingsPage, {
      global: {
        plugins: [[VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    const input = await screen.findByLabelText('Cookie')
    await waitFor(() => expect(input).toHaveValue('PHPSESSID=stored'))

    await user.clear(input)
    await user.type(input, 'PHPSESSID=updated')
    const qualitySlider = screen.getByRole('slider')
    qualitySlider.focus()
    await user.keyboard('{ArrowLeft}')
    await user.click(screen.getByRole('switch'))
    await user.click(screen.getByRole('button', { name: '保存设置' }))

    await waitFor(() => expect(pixivCookie).toBe('PHPSESSID=updated'))
    expect(webpEnabled).toBe(false)
    expect(webpQuality).toBe(84)
    expect(input).toHaveValue('PHPSESSID=updated')
    expect(screen.getByText('设置已保存。')).toBeInTheDocument()
  })
})
