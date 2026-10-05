import type { CropOptions, CropResult } from 'smartcrop'
import { vi } from 'vitest'

import { analyzeSmartCrop } from '@/shared/lib/smart-crop'

type Crop = (image: CanvasImageSource, options: CropOptions) => Promise<CropResult>

const { cropMock } = vi.hoisted(() => ({ cropMock: vi.fn<Crop>() }))

vi.mock('smartcrop', () => ({
  default: { crop: cropMock },
}))

function imageWithNaturalSize(width: number, height: number) {
  const image = document.createElement('img')
  Object.defineProperties(image, {
    naturalWidth: { configurable: true, value: width },
    naturalHeight: { configurable: true, value: height },
  })
  return image
}

describe('智能裁剪分析', () => {
  beforeEach(() => cropMock.mockReset())

  it('将裁剪区域换算为对象位置百分比', async () => {
    cropMock.mockResolvedValue({
      topCrop: { x: 160, y: 0, width: 200, height: 200 },
    })
    const image = imageWithNaturalSize(400, 200)

    await expect(analyzeSmartCrop(image, '/position-test', 1, 1)).resolves.toEqual({
      x: 80,
      y: 50,
    })
  })

  it('合并同一图片和裁剪比例的并发分析', async () => {
    cropMock.mockResolvedValue({
      topCrop: { x: 0, y: 160, width: 200, height: 200 },
    })
    const image = imageWithNaturalSize(200, 400)

    const first = analyzeSmartCrop(image, '/deduplication-test', 1, 1)
    const second = analyzeSmartCrop(image, '/deduplication-test', 1, 1)

    await expect(Promise.all([first, second])).resolves.toEqual([
      { x: 50, y: 80 },
      { x: 50, y: 80 },
    ])
    expect(cropMock).toHaveBeenCalledOnce()
  })
})
