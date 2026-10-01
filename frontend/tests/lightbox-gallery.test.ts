import { fireEvent, render, waitFor } from '@testing-library/vue'
import type Viewer from 'viewerjs'
import { vi } from 'vitest'
import { h } from 'vue'

import LightboxGallery from '@ui/LightboxGallery.vue'

const { constructorMock, destroyMock, updateMock, viewMock } = vi.hoisted(() => ({
  constructorMock: vi.fn(),
  destroyMock: vi.fn(),
  updateMock: vi.fn(),
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
      updateMock()
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
    updateMock.mockReset()
    viewMock.mockReset()
  })

  it('通过插槽打开指定图片并启用克制的预览交互', async () => {
    const view = render(LightboxGallery, {
      props: {
        items: [
          { src: '/api/artworks/123/pages/0', alt: '测试作品 第 1 页' },
          { src: '/api/artworks/123/pages/1', alt: '测试作品 第 2 页' },
        ],
      },
      slots: { default: triggerSlot(1) },
    })

    expect(constructorMock).not.toHaveBeenCalled()
    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await waitFor(() => expect(constructorMock).toHaveBeenCalledOnce())

    const options = getOptions()
    const sourceImages = [...view.container.querySelectorAll('img')]

    expect(
      sourceImages.map((image) => ({ src: image.getAttribute('src'), alt: image.alt })),
    ).toEqual([
      { src: '/api/artworks/123/pages/0', alt: '测试作品 第 1 页' },
      { src: '/api/artworks/123/pages/1', alt: '测试作品 第 2 页' },
    ])
    expect(options).toMatchObject({
      className: 'artwork-lightbox',
      backdrop: true,
      button: false,
      title: false,
      toolbar: false,
      navbar: { show: true, size: 'large' },
      navigation: {
        prev: { show: true, size: 'large' },
        next: { show: true, size: 'large' },
      },
      keyboard: true,
      loop: false,
      zoomable: true,
      slideOnWheel: false,
      rotatable: false,
      scalable: false,
      tooltip: false,
    })
    expect(options).not.toHaveProperty('initialViewIndex')
    expect(options).not.toHaveProperty('movable')
    expect(options).not.toHaveProperty('move')
    expect(options).not.toHaveProperty('zoom')
    expect(options).not.toHaveProperty('zoomed')
    expect(options).not.toHaveProperty('transition')
    expect(options).not.toHaveProperty('toggleOnDblclick')
    expect(viewMock).toHaveBeenCalledWith(1)

    const imageData = { naturalWidth: 2000, naturalHeight: 1000 }
    const minimum = (options.minZoomRatio as Exclude<Viewer.ZoomRatio, number>).call(
      {} as Viewer,
      document.createElement('img'),
      imageData,
    )
    const maximum = (options.maxZoomRatio as Exclude<Viewer.ZoomRatio, number>).call(
      {} as Viewer,
      document.createElement('img'),
      imageData,
    )
    expect(minimum).toBeGreaterThan(0)
    expect(maximum / minimum).toBe(8)
  })

  it('同步页码并在首尾隐藏对应的换页热区', async () => {
    const onChange = vi.fn()
    const view = render(LightboxGallery, {
      props: {
        items: [
          { src: '/api/artworks/123/pages/0', alt: '第一页' },
          { src: '/api/artworks/123/pages/1', alt: '第二页' },
        ],
        onChange,
      },
      slots: { default: triggerSlot() },
    })

    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await waitFor(() => expect(constructorMock).toHaveBeenCalledOnce())

    const options = getOptions()
    const root = document.createElement('div')
    const previous = document.createElement('div')
    const next = document.createElement('div')
    const image = document.createElement('img')
    root.className = 'artwork-lightbox'
    previous.className = 'viewer-prev viewer-hide'
    next.className = 'viewer-next'
    root.append(previous, image, next)

    options.viewed?.(
      new CustomEvent('viewed', {
        detail: { image, index: 1, originalImage: image, originalEvent: null },
      }),
    )

    expect(onChange).toHaveBeenCalledWith(1)
    expect(previous).not.toHaveClass('viewer-hide')
    expect(next).toHaveClass('viewer-hide')
  })

  it('在图片结构不变时更新已有实例', async () => {
    const view = render(LightboxGallery, {
      props: {
        items: [
          { src: '/api/artworks/123/pages/0', alt: '第一页' },
          { src: '/api/artworks/123/pages/1', alt: '第二页' },
        ],
      },
      slots: { default: triggerSlot() },
    })

    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await view.rerender({
      items: [
        { src: '/api/artworks/123/pages/0', alt: '更新后的第一页' },
        { src: '/api/artworks/123/pages/1', alt: '第二页' },
      ],
    })

    await waitFor(() => expect(updateMock).toHaveBeenCalledOnce())
    expect(destroyMock).not.toHaveBeenCalled()
  })

  it('图片结构变化时重建实例，并在卸载时清理', async () => {
    const view = render(LightboxGallery, {
      props: {
        items: [{ src: '/api/artworks/123/pages/0', alt: '第一页' }],
      },
      slots: { default: triggerSlot() },
    })

    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await waitFor(() => expect(constructorMock).toHaveBeenCalledOnce())
    await view.rerender({
      items: [
        { src: '/api/artworks/123/pages/0', alt: '第一页' },
        { src: '/api/artworks/123/pages/1', alt: '第二页' },
      ],
    })

    await waitFor(() => expect(destroyMock).toHaveBeenCalledOnce())
    expect(constructorMock).toHaveBeenCalledOnce()

    await fireEvent.click(view.getByRole('button', { name: '打开预览' }))
    await waitFor(() => expect(constructorMock).toHaveBeenCalledTimes(2))
    expect(getOptions(1).navbar).toEqual({ show: true, size: 'large' })

    view.unmount()
    expect(destroyMock).toHaveBeenCalledTimes(2)
  })
})
