import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { CropOptions, CropResult } from 'smartcrop'
import { vi } from 'vitest'

import SmartCropImage from '@ui/SmartCropImage.vue'

type Crop = (image: CanvasImageSource, options: CropOptions) => Promise<CropResult>

const { cropMock } = vi.hoisted(() => ({ cropMock: vi.fn<Crop>() }))

vi.mock('smartcrop', () => ({
  default: { crop: cropMock },
}))

function setNaturalSize(image: HTMLImageElement, width: number, height: number) {
  Object.defineProperties(image, {
    naturalWidth: { configurable: true, value: width },
    naturalHeight: { configurable: true, value: height },
  })
}

function getImage(name: string) {
  const image = screen.getByRole('img', { name })
  if (!(image instanceof HTMLImageElement)) throw new Error('目标元素不是图片。')
  return image
}

describe('智能裁剪图片', () => {
  beforeEach(() => {
    cropMock.mockReset()
  })

  it('针对指定比例分析图片并换算 object-position', async () => {
    cropMock.mockResolvedValue({
      topCrop: { x: 160, y: 0, width: 200, height: 200 },
    })
    render(SmartCropImage, {
      props: {
        src: '/api/artworks/123/thumbnail?position-test',
        alt: '测试作品',
        cropWidth: 1,
        cropHeight: 1,
      },
      attrs: {
        class: 'size-full object-cover',
        loading: 'lazy',
        style: { backgroundColor: 'rgb(1, 2, 3)' },
      },
    })

    const image = getImage('测试作品')
    setNaturalSize(image, 400, 200)
    await fireEvent.load(image)

    await waitFor(() => {
      expect(cropMock).toHaveBeenCalledWith(image, {
        width: 1,
        height: 1,
        minScale: 1,
        ruleOfThirds: true,
      })
      expect(image).toHaveStyle({ objectPosition: '80% 50%' })
    })
    expect(image).toHaveStyle({ backgroundColor: 'rgb(1, 2, 3)' })
    expect(image).toHaveClass('size-full', 'object-cover')
    expect(image).toHaveAttribute('loading', 'lazy')
  })

  it('分析失败时保持居中裁剪并继续触发原生事件', async () => {
    cropMock.mockRejectedValue(new Error('canvas unavailable'))
    const onLoad = vi.fn()
    render(SmartCropImage, {
      props: { src: '/api/artworks/456/thumbnail?fallback-test', alt: '回退测试', onLoad },
    })

    const image = getImage('回退测试')
    setNaturalSize(image, 200, 400)
    await fireEvent.load(image)

    await waitFor(() => {
      expect(cropMock).toHaveBeenCalledOnce()
      expect(image).toHaveStyle({ objectPosition: '50% 50%' })
    })
    expect(onLoad).toHaveBeenCalledOnce()
  })

  it('相同图片和裁剪比例共享一次分析', async () => {
    cropMock.mockResolvedValue({
      topCrop: { x: 0, y: 160, width: 200, height: 200 },
    })
    render({
      components: { SmartCropImage },
      template: `
        <SmartCropImage src="/api/artworks/789/thumbnail?cache-test" alt="缓存测试一" />
        <SmartCropImage src="/api/artworks/789/thumbnail?cache-test" alt="缓存测试二" />
      `,
    })

    const firstImage = getImage('缓存测试一')
    const secondImage = getImage('缓存测试二')
    setNaturalSize(firstImage, 200, 400)
    setNaturalSize(secondImage, 200, 400)
    await Promise.all([fireEvent.load(firstImage), fireEvent.load(secondImage)])

    await waitFor(() => {
      expect(cropMock).toHaveBeenCalledOnce()
      expect(firstImage).toHaveStyle({ objectPosition: '50% 80%' })
      expect(secondImage).toHaveStyle({ objectPosition: '50% 80%' })
    })
  })
})
