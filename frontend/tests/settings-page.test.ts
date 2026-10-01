import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import SettingsPage from '@/pages/settings/SettingsPage.vue'
import { toast } from '@ui/toast'
import ToastHost from '@ui/ToastHost.vue'

let pixivCookie = 'PHPSESSID=stored'
let downloadConcurrency = 3
let requestIntervalMs = 500
let webpEnabled = true
let webpQuality = 85
let cookieValid = true
let settingPatches: Record<string, unknown>[] = []
let intersectionCallback: IntersectionObserverCallback

const observeSection = vi.fn()
const scrollIntoView = vi.fn()

function settingsPayload() {
  return {
    pixivCookie: pixivCookie || null,
    proxyUrl: null,
    libraryRoot: 'C:\\PiPerch\\library',
    downloadConcurrency,
    requestIntervalMs,
    webpEnabled,
    webpQuality,
  }
}

class IntersectionObserverMock {
  readonly root = null
  readonly rootMargin = '0px'
  readonly thresholds = [0]

  constructor(callback: IntersectionObserverCallback) {
    intersectionCallback = callback
  }

  observe(element: Element) {
    observeSection(element)
  }

  unobserve() {
    return undefined
  }

  disconnect() {
    return undefined
  }

  takeRecords() {
    return []
  }
}

const server = setupServer(
  http.get('/api/settings', () => HttpResponse.json(settingsPayload())),
  http.patch('/api/settings', async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>
    settingPatches.push(patch)
    if ('pixivCookie' in patch) pixivCookie = (patch.pixivCookie as string | null) ?? ''
    if ('downloadConcurrency' in patch) downloadConcurrency = patch.downloadConcurrency as number
    if ('requestIntervalMs' in patch) requestIntervalMs = patch.requestIntervalMs as number
    if ('webpEnabled' in patch) webpEnabled = patch.webpEnabled as boolean
    if ('webpQuality' in patch) webpQuality = patch.webpQuality as number
    return HttpResponse.json(settingsPayload())
  }),
  http.post('/api/settings/pixiv-cookie/validate', () => HttpResponse.json({ valid: cookieValid })),
)

function renderSettingsPage() {
  return render(
    {
      components: { SettingsPage, ToastHost },
      template: '<SettingsPage /><ToastHost />',
    },
    {
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
    },
  )
}

function intersectSection(section: Element) {
  intersectionCallback(
    [
      {
        isIntersecting: true,
        target: section,
        boundingClientRect: { top: 64 },
      } as IntersectionObserverEntry,
    ],
    {} as IntersectionObserver,
  )
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  pixivCookie = 'PHPSESSID=stored'
  downloadConcurrency = 3
  requestIntervalMs = 500
  webpEnabled = true
  webpQuality = 85
  cookieValid = true
  settingPatches = []
  observeSection.mockClear()
  scrollIntoView.mockClear()
  vi.stubGlobal('IntersectionObserver', IntersectionObserverMock)
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: scrollIntoView,
  })
})
afterEach(() => {
  toast.dismiss()
  server.resetHandlers()
})
afterAll(() => server.close())

describe('设置页', () => {
  it('使用子侧栏导航全部设置小节并同步滚动状态', async () => {
    const user = userEvent.setup()
    renderSettingsPage()

    await screen.findByDisplayValue('PHPSESSID=stored')
    const navigation = screen.getByRole('navigation')
    const navigationButtons = within(navigation).getAllByRole('button')
    expect(navigationButtons.map((button) => button.textContent.trim())).toEqual([
      'Pixiv',
      '下载与网络',
      '存储',
    ])
    expect(document.querySelectorAll('[data-setting-item]')).toHaveLength(7)
    expect(screen.getByText('Cookie').closest('[data-setting-item]')).toHaveAttribute(
      'data-layout',
      'expanded',
    )
    expect(screen.getByText('HTTP/HTTPS 代理').closest('[data-setting-item]')).toHaveAttribute(
      'data-layout',
      'compact',
    )
    expect(observeSection).toHaveBeenCalledTimes(3)

    const storageButton = within(navigation).getByRole('button', { name: '存储' })
    const storageSection = document.getElementById('settings-storage')
    if (!storageSection) throw new Error('未找到存储设置小节。')
    await user.click(storageButton)
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })

    intersectSection(storageSection)
    await waitFor(() => expect(storageButton).toHaveClass('bg-sidebar-accent'))

    expect(screen.queryByRole('button', { name: '保存设置' })).not.toBeInTheDocument()
  })

  it('在各设置项的交互完成时分别提交修改', async () => {
    const user = userEvent.setup()
    renderSettingsPage()

    const input = await screen.findByLabelText('Cookie')
    await waitFor(() => expect(input).toHaveValue('PHPSESSID=stored'))
    await user.clear(input)
    await user.type(input, 'PHPSESSID=updated')
    await user.tab()

    const qualitySlider = screen.getByRole('slider')
    qualitySlider.focus()
    await user.keyboard('{ArrowLeft}')
    await user.click(screen.getByRole('switch'))

    const qualityItem = screen.getByText('WebP 质量').closest('[data-setting-item]')
    expect(qualityItem).toHaveAttribute('data-disabled', 'true')
    expect(qualitySlider).toHaveAttribute('data-disabled')

    await waitFor(() => expect(pixivCookie).toBe('PHPSESSID=updated'))
    await waitFor(() => expect(webpEnabled).toBe(false))
    await waitFor(() => expect(webpQuality).toBe(84))
    expect(settingPatches).toEqual(
      expect.arrayContaining([
        { pixivCookie: 'PHPSESSID=updated' },
        { webpQuality: 84 },
        { webpEnabled: false },
      ]),
    )
    expect(settingPatches.every((patch) => Object.keys(patch).length === 1)).toBe(true)
    expect(input).toHaveValue('PHPSESSID=updated')
    expect(await screen.findByText('Cookie已保存')).toBeInTheDocument()
  })

  it('数字输入只在失焦得到有效值时保存当前设置项', async () => {
    const user = userEvent.setup()
    renderSettingsPage()

    const concurrencyInput = await screen.findByLabelText('媒体并发数')
    await user.clear(concurrencyInput)
    await user.type(concurrencyInput, '6')
    await user.tab()

    await waitFor(() => expect(downloadConcurrency).toBe(6))
    expect(settingPatches).toContainEqual({ downloadConcurrency: 6 })

    await user.clear(concurrencyInput)
    await user.type(concurrencyInput, '9')
    await user.tab()

    expect(concurrencyInput).toHaveValue(6)
    expect(downloadConcurrency).toBe(6)
    expect(settingPatches.filter((patch) => 'downloadConcurrency' in patch)).toHaveLength(1)
  })

  it('单个设置项保存失败时显示对应错误', async () => {
    server.use(
      http.patch('/api/settings', () =>
        HttpResponse.json(
          { error: { code: 'save_failed', message: '无法保存并发数' } },
          { status: 500 },
        ),
      ),
    )
    const user = userEvent.setup()
    renderSettingsPage()

    const concurrencyInput = await screen.findByLabelText('媒体并发数')
    await user.clear(concurrencyInput)
    await user.type(concurrencyInput, '4')
    await user.tab()

    expect(await screen.findByText('媒体并发数保存失败')).toBeInTheDocument()
    expect(screen.getByText('无法保存并发数')).toBeInTheDocument()
  })

  it('分别反馈 Cookie 验证成功、无效和接口错误', async () => {
    const user = userEvent.setup()
    renderSettingsPage()

    await screen.findByDisplayValue('PHPSESSID=stored')
    const validateButton = screen.getByRole('button', { name: '验证' })

    await user.click(validateButton)
    expect(await screen.findByText('Cookie 验证通过')).toBeInTheDocument()

    cookieValid = false
    await user.click(validateButton)
    expect(await screen.findByText('Cookie 无效或已过期')).toBeInTheDocument()

    server.use(
      http.post('/api/settings/pixiv-cookie/validate', () =>
        HttpResponse.json(
          { error: { code: 'validation_failed', message: '验证服务不可用' } },
          { status: 503 },
        ),
      ),
    )
    await user.click(validateButton)
    expect(await screen.findByText('Cookie 验证失败')).toBeInTheDocument()
    expect(screen.getByText('验证服务不可用')).toBeInTheDocument()
  })

  it('加载设置失败时显示错误 Toast', async () => {
    server.use(
      http.get('/api/settings', () =>
        HttpResponse.json(
          { error: { code: 'load_failed', message: '无法读取设置' } },
          { status: 500 },
        ),
      ),
    )

    renderSettingsPage()

    expect(await screen.findByText('加载设置失败')).toBeInTheDocument()
    expect(screen.getByText('无法读取设置')).toBeInTheDocument()
  })
})
