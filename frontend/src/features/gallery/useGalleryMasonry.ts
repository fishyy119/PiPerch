import type { VirtualItem, Virtualizer } from '@tanstack/vue-virtual'
import { defaultRangeExtractor, useWindowVirtualizer } from '@tanstack/vue-virtual'
import { useResizeObserver } from '@vueuse/core'
import type { Ref } from 'vue'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { usePreference } from '@/app/usePreference'
import type { GalleryMediaItem } from '@/features/gallery/gallery-media'

const IMAGE_GAP = 8
// 为页面顶部的固定工具栏预留滚动空间，与图片内容无关。
const TOPBAR_HEIGHT = 64

interface MasonryAnchor {
  key: string
  offset: number
}

// 仅保存最近一次浏览位置，返回详情来源时仍以图片身份恢复，而非依赖旧列宽。
let savedPosition: { stateKey: string; anchor: MasonryAnchor } | undefined

export function useGalleryMasonry(
  root: Ref<HTMLElement | null>,
  items: Readonly<Ref<readonly GalleryMediaItem[]>>,
) {
  // 在创建时捕获图库路由，卸载时当前路由可能已切换到详情页。
  const stateKey = useRoute().fullPath
  const imageWidth = usePreference('gallery.masonryImageWidth')
  const containerWidth = ref(0)
  const scrollMargin = ref(0)
  const focusedKey = ref<string | null>(null)
  let anchor: MasonryAnchor | undefined
  let disposed = false
  let restoreFrame: number | undefined

  const columns = computed(() =>
    Math.max(1, Math.floor((containerWidth.value + IMAGE_GAP) / (imageWidth.value + IMAGE_GAP))),
  )
  const columnWidth = computed(() =>
    Math.max(1, (containerWidth.value - (columns.value - 1) * IMAGE_GAP) / columns.value),
  )
  const itemIndexes = computed(() => new Map(items.value.map((item, index) => [item.key, index])))

  function visibleAnchor(instance: Virtualizer<Window, HTMLElement>): MasonryAnchor | undefined {
    const offset = instance.scrollOffset ?? window.scrollY
    const bottom = offset + window.innerHeight
    const candidates = instance
      .getVirtualItems()
      .filter((item) => item.end > offset + TOPBAR_HEIGHT && item.start < bottom)
    const item = candidates.reduce<VirtualItem | undefined>(
      (nearest, candidate) =>
        !nearest ||
        Math.abs(candidate.start - offset - TOPBAR_HEIGHT) <
          Math.abs(nearest.start - offset - TOPBAR_HEIGHT)
          ? candidate
          : nearest,
      undefined,
    )
    const key = item && items.value[item.index]?.key
    return item && key ? { key, offset: item.start - offset } : undefined
  }

  const virtualizer = useWindowVirtualizer<HTMLElement>(
    computed(() => {
      const focusedIndex =
        focusedKey.value === null ? undefined : itemIndexes.value.get(focusedKey.value)
      return {
        enabled: root.value !== null && containerWidth.value > 0,
        count: items.value.length,
        lanes: columns.value,
        gap: IMAGE_GAP,
        scrollMargin: scrollMargin.value,
        scrollPaddingStart: TOPBAR_HEIGHT,
        estimateSize: (index: number) => columnWidth.value / (items.value[index]?.aspectRatio ?? 1),
        getItemKey: (index: number) => items.value[index]?.key ?? index,
        overscan: 6,
        rangeExtractor: (range: Parameters<typeof defaultRangeExtractor>[0]) => {
          const indexes = defaultRangeExtractor(range)
          return focusedIndex === undefined || indexes.includes(focusedIndex)
            ? indexes
            : [...indexes, focusedIndex].sort((left, right) => left - right)
        },
        onChange: (instance: Virtualizer<Window, HTMLElement>, sync: boolean) => {
          if (sync || !anchor) anchor = visibleAnchor(instance)
        },
      }
    }),
  )

  const visibleItems = computed(() => {
    const instance = virtualizer.value
    const buffer = Math.max(600, (instance.scrollRect?.height ?? window.innerHeight) * 0.75)
    const top = (instance.scrollOffset ?? window.scrollY) - buffer
    const bottom = (instance.scrollOffset ?? window.scrollY) + window.innerHeight + buffer
    // 极长图会拉大库返回的连续索引范围，按实际区间过滤，保持挂载数量受控。
    return instance
      .getVirtualItems()
      .filter(
        (item) =>
          (item.end >= top && item.start <= bottom) ||
          items.value[item.index]?.key === focusedKey.value,
      )
  })
  const totalHeight = computed(() => virtualizer.value.getTotalSize())

  async function restorePosition(position: MasonryAnchor) {
    await nextTick()
    if (disposed) return
    const index = itemIndexes.value.get(position.key)
    if (index === undefined) return
    virtualizer.value.scrollToIndex(index, { align: 'start' })
    if (restoreFrame !== undefined) cancelAnimationFrame(restoreFrame)
    restoreFrame = requestAnimationFrame(() => {
      const item = virtualizer.value.getVirtualItems().find((entry) => entry.index === index)
      if (item) {
        virtualizer.value.scrollToOffset(item.start - position.offset)
        anchor = position
      }
    })
  }

  function updateGeometry() {
    if (!root.value) return
    containerWidth.value = root.value.clientWidth
    scrollMargin.value = root.value.getBoundingClientRect().top + window.scrollY
  }
  // 只在图片身份、比例或容器几何变化时重排，忽略其他作品信息的刷新。
  watch(
    [
      columnWidth,
      columns,
      scrollMargin,
      () => items.value.map((item) => `${item.key}:${String(item.aspectRatio)}`).join(','),
    ],
    (_layout, [previousWidth]) => {
      const previous = anchor
      virtualizer.value.measure()
      if (previous && containerWidth.value > 0 && previousWidth > 1) void restorePosition(previous)
    },
    { flush: 'post' },
  )
  useResizeObserver(root, updateGeometry)
  watch(
    root,
    (element) => {
      if (!element) return
      const position =
        anchor ?? (savedPosition?.stateKey === stateKey ? savedPosition.anchor : undefined)
      updateGeometry()
      if (position) void restorePosition(position)
    },
    { flush: 'post' },
  )
  onBeforeUnmount(() => {
    disposed = true
    if (restoreFrame !== undefined) cancelAnimationFrame(restoreFrame)
    const current = visibleAnchor(virtualizer.value) ?? anchor
    if (current) savedPosition = { stateKey, anchor: current }
  })

  return {
    visibleItems,
    totalHeight,
    columnWidth,
    gap: IMAGE_GAP,
    scrollMargin,
    focusedKey,
  }
}
