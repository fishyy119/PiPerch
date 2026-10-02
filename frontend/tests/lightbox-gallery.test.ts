import { fireEvent, render, waitFor } from '@testing-library/vue'
import type Viewer from 'viewerjs'
import { vi } from 'vitest'
import { h } from 'vue'

import LightboxGallery from '@ui/LightboxGallery.vue'

const { constructorMock, destroyMock, viewMock } = vi.hoisted(() => ({
  constructorMock: vi.fn(),
  destroyMock: vi.fn(),
  viewMock: vi.fn(),
}))

vi.mock('viewerjs', () => ({
  default: class ViewerMock {
    constructor(element: HTMLElement, options: Viewer.Options) {
      constructorMock(element, options)
    }

    destroy() {
      destroyMock()
      return this
    }

    update() {
      return this
    }

    view(index: number) {
      viewMock(index)
      return this
    }
  },
}))

function getOptions(callIndex = 0) {
  const call = constructorMock.mock.calls[callIndex]
  if (call === undefined) throw new Error('Viewer 构造函数未被调用。')
  return call[1] as Viewer.Options
}

function triggerSlot(index = 0) {
  return ({ open }: { open: (index?: number) => void }) =>
    h('button', { type: 'button', onClick: () => open(index) }, '打开预览')
}

describe('LightboxGallery', () => {
  beforeEach(() => {
    constructorMock.mockReset()
    destroyMock.mockReset()
    viewMock.mockReset()
  })

  it('按指定索引打开、关闭时同步页码并在卸载时清理', async () => {
    const onChange = vi.fn()
    const view = render(LightboxGallery, {
      props: {
        items: [
          {
            src: '/api/artworks/123/pages/0',
            thumbnailSrc: '/api/artworks/123/pages/0/thumbnail',
            alt: '测试作品 第 1 页',
          },
          {
            src: '/api/artworks/123/pages/1',
            thumbnailSrc: '/api/artworks/123/pages/1/thumbnail',
            alt: '测试作品 第 2 页',
          },
        ],
        onChange,
      },
      slots: { default: triggerSlot(1) },
    })

    expect(constructorMock).not.toHaveBeenCalled()
    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await waitFor(() => expect(constructorMock).toHaveBeenCalledOnce())

    expect(viewMock).toHaveBeenCalledWith(1)

    const options = getOptions()
    expect(options.navbar).toEqual({ show: true, size: 'large' })
    expect(options.url).toBe('data-original-src')
    expect(view.container.querySelector('img')).toHaveAttribute(
      'src',
      '/api/artworks/123/pages/0/thumbnail',
    )
    expect(view.container.querySelector('img')).toHaveAttribute(
      'data-original-src',
      '/api/artworks/123/pages/0',
    )
    const image = document.createElement('img')
    options.viewed?.(
      new CustomEvent('viewed', {
        detail: { image, index: 1, originalImage: image, originalEvent: null },
      }),
    )

    expect(onChange).not.toHaveBeenCalled()
    options.hidden?.(
      new CustomEvent('hidden', {
        detail: { originalEvent: null },
      }),
    )

    expect(onChange).toHaveBeenCalledWith(1)
    view.unmount()
    expect(destroyMock).toHaveBeenCalledOnce()
  })
})
