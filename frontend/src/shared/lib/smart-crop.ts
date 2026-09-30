import smartcrop from 'smartcrop'

export type SmartCropPosition = Readonly<{
  x: number
  y: number
}>

type CropJob = Readonly<{
  run: () => Promise<void>
}>

const cropCache = new Map<string, SmartCropPosition>()
const pendingCrops = new Map<string, Promise<SmartCropPosition>>()
const cropQueue: CropJob[] = []
let cropJobScheduled = false

function percentagePosition(offset: number, imageSize: number, cropSize: number) {
  const availableOffset = imageSize - cropSize
  if (availableOffset <= 0) return 50
  return Math.min(100, Math.max(0, (offset / availableOffset) * 100))
}

function runNextCropJob() {
  cropJobScheduled = false
  const job = cropQueue.shift()
  if (job === undefined) return

  void job.run().finally(scheduleNextCropJob)
}

function scheduleNextCropJob() {
  if (cropJobScheduled || cropQueue.length === 0) return
  cropJobScheduled = true

  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(runNextCropJob, { timeout: 250 })
    return
  }
  window.setTimeout(runNextCropJob, 0)
}

function enqueueCrop(run: () => Promise<SmartCropPosition>) {
  return new Promise<SmartCropPosition>((resolve, reject) => {
    cropQueue.push({
      run: async () => {
        try {
          resolve(await run())
        } catch (error: unknown) {
          reject(error instanceof Error ? error : new Error('智能裁剪分析失败。'))
        }
      },
    })
    scheduleNextCropJob()
  })
}

function cropCacheKey(image: HTMLImageElement, src: string, cropWidth: number, cropHeight: number) {
  return [
    src,
    `${String(image.naturalWidth)}x${String(image.naturalHeight)}`,
    `${String(cropWidth)}:${String(cropHeight)}`,
  ].join('|')
}

export function analyzeSmartCrop(
  image: HTMLImageElement,
  src: string,
  cropWidth: number,
  cropHeight: number,
) {
  const cacheKey = cropCacheKey(image, src, cropWidth, cropHeight)
  const cached = cropCache.get(cacheKey)
  if (cached !== undefined) return Promise.resolve(cached)

  const pending = pendingCrops.get(cacheKey)
  if (pending !== undefined) return pending

  const analysis = enqueueCrop(async () => {
    const result = await smartcrop.crop(image, {
      width: cropWidth,
      height: cropHeight,
      minScale: 1, // 裁剪窗口必须保持为能够容纳的最大尺寸
      ruleOfThirds: true,
    })
    const position = {
      x: percentagePosition(result.topCrop.x, image.naturalWidth, result.topCrop.width),
      y: percentagePosition(result.topCrop.y, image.naturalHeight, result.topCrop.height),
    }
    cropCache.set(cacheKey, position)
    return position
  })
  pendingCrops.set(cacheKey, analysis)
  void analysis.finally(() => pendingCrops.delete(cacheKey)).catch(() => undefined)
  return analysis
}
