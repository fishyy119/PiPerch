<script lang="ts">
export interface LightboxItem {
  src: string
  thumbnailSrc?: string
  alt: string
}
</script>

<script setup lang="ts">
import 'viewerjs/dist/viewer.css'

import Viewer from 'viewerjs'
import { onBeforeUnmount, ref, watch } from 'vue'

const NAVBAR_HEIGHT = 60

const props = defineProps<{
  items: readonly LightboxItem[]
}>()

defineSlots<{
  default(props: { open: (index?: number) => void }): unknown
}>()

const emit = defineEmits<{
  change: [index: number]
}>()

const galleryElement = ref<HTMLElement>()

let instance: Viewer | undefined
let instanceHasMultipleItems = false
let pendingIndex = 0
let syncOnHidden = false

function normalizedIndex(index: number) {
  if (!Number.isInteger(index)) return 0
  return Math.min(Math.max(index, 0), Math.max(props.items.length - 1, 0))
}

function navbarHeight() {
  return props.items.length > 1 ? NAVBAR_HEIGHT : 0
}

function initialCoverage() {
  const margin = window.innerWidth >= 640 ? 32 : 16
  const availableHeight = Math.max(window.innerHeight - navbarHeight(), 1)

  return Math.max(
    0.1,
    Math.min(
      1,
      (window.innerWidth - margin * 2) / window.innerWidth,
      (availableHeight - margin * 2) / availableHeight,
    ),
  )
}

function initialImageRatio(imageData: Record<string, unknown>, coverage: number) {
  const naturalWidth = Number(imageData.naturalWidth)
  const naturalHeight = Number(imageData.naturalHeight)
  if (naturalWidth <= 0 || naturalHeight <= 0) return 1

  const availableHeight = Math.max(window.innerHeight - navbarHeight(), 1)
  const fittedRatio = Math.min(window.innerWidth / naturalWidth, availableHeight / naturalHeight)
  return Math.min(1, fittedRatio * coverage)
}

function updateBoundaryNavigation(event: Viewer.ViewedEvent) {
  const { image, index } = event.detail
  const viewer = image.closest('.artwork-lightbox')
  viewer?.querySelector('.viewer-prev')?.classList.toggle('viewer-hide', index <= 0)
  viewer
    ?.querySelector('.viewer-next')
    ?.classList.toggle('viewer-hide', index >= props.items.length - 1)
}

function destroyViewer() {
  const currentInstance = instance
  instance = undefined
  instanceHasMultipleItems = false
  syncOnHidden = false
  currentInstance?.destroy()
}

function openLightbox(index = 0) {
  if (props.items.length === 0) return

  pendingIndex = normalizedIndex(index)
  syncOnHidden = true

  if (instance === undefined) {
    const element = galleryElement.value
    if (element === undefined) return

    const multiple = props.items.length > 1
    const coverage = initialCoverage()
    instanceHasMultipleItems = multiple
    instance = new Viewer(element, {
      className: 'artwork-lightbox',
      initialCoverage: coverage,
      backdrop: true,
      button: false,
      title: false,
      toolbar: false,
      navbar: multiple ? { show: true, size: 'large' } : false,
      navigation: multiple
        ? {
            prev: { show: true, size: 'large' },
            next: { show: true, size: 'large' },
          }
        : false,
      keyboard: true,
      loop: false,
      zoomable: true,
      zoomOnWheel: true,
      zoomOnTouch: true,
      zoomOnGesture: true,
      slideOnTouch: true,
      slideOnWheel: false,
      rotatable: false,
      rotateOnGesture: false,
      rotateOnTouch: false,
      scalable: false,
      magnifier: false,
      tooltip: false,
      url: 'data-original-src',
      minZoomRatio: (_image, imageData) => initialImageRatio(imageData, coverage) * 0.5,
      maxZoomRatio: (_image, imageData) => initialImageRatio(imageData, coverage) * 4,
      viewed: (event) => {
        pendingIndex = event.detail.index
        updateBoundaryNavigation(event)
      },
      hidden: () => {
        if (!syncOnHidden) return
        syncOnHidden = false
        emit('change', pendingIndex)
      },
    })
  }

  instance.view(pendingIndex)
}

watch(
  () => props.items,
  () => {
    if (instance === undefined) return

    const hasMultipleItems = props.items.length > 1
    if (props.items.length === 0 || hasMultipleItems !== instanceHasMultipleItems) {
      destroyViewer()
      return
    }

    instance.update()
  },
  { flush: 'post' },
)

onBeforeUnmount(() => {
  destroyViewer()
})
</script>

<template>
  <slot :open="openLightbox" />
  <div ref="galleryElement" hidden>
    <img
      v-for="item in items"
      :key="item.src"
      :src="item.thumbnailSrc ?? item.src"
      :data-original-src="item.src"
      :alt="item.alt"
      loading="lazy"
      decoding="async"
    />
  </div>
</template>

<style>
/* 使遮罩与图片始终使用普通光标，覆盖 Viewer.js 的抓取光标。 */
.artwork-lightbox,
.artwork-lightbox .viewer-canvas > img {
  cursor: default;
}

/* 缩短 Viewer.js 根容器和内部元素的过渡时间。 */
.artwork-lightbox.viewer-transition,
.artwork-lightbox .viewer-transition {
  transition-duration: 120ms;
}

/* 使导航层避开底部缩略图，并让非按钮区域继续响应图片或背景操作。 */
.artwork-lightbox .viewer-navigation {
  inset: 0 0 60px;
  pointer-events: none;
}

/* 将默认圆形按钮扩展为无边框的整列翻页热区。 */
.artwork-lightbox .viewer-navigation > :is(.viewer-prev, .viewer-next) {
  top: 0;
  bottom: 0;
  width: clamp(4rem, 12vw, 10rem);
  height: auto;
  margin: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  cursor: default;
  pointer-events: auto;
}

/* 将上一页热区贴齐左边缘，并记录渐变方向。 */
.artwork-lightbox .viewer-navigation > .viewer-prev {
  --navigation-gradient-direction: to right;

  left: 0;
}

/* 将下一页热区贴齐右边缘，并记录渐变方向。 */
.artwork-lightbox .viewer-navigation > .viewer-next {
  --navigation-gradient-direction: to left;

  right: 0;
}

/* 将 Viewer.js 自带的箭头图标放在侧边热区中央。 */
.artwork-lightbox .viewer-navigation > :is(.viewer-prev, .viewer-next)::before {
  position: absolute;
  top: 50%;
  left: 50%;
  margin: 0;
  transform: translate(-50%, -50%);
}

/* 在侧边热区悬停或键盘聚焦时，显示从窗口边缘淡出的渐变。 */
.artwork-lightbox .viewer-navigation > :is(.viewer-prev, .viewer-next):is(:hover, :focus-visible) {
  background: linear-gradient(var(--navigation-gradient-direction), rgb(0 0 0 / 38%), transparent);
}
</style>
