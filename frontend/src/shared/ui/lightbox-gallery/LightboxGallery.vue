<script lang="ts">
export interface LightboxItem {
  key: string
  src: string
  alt: string
}

export interface LightboxAction {
  title: string
  icon: string
  action: (item: LightboxItem) => void
}
</script>

<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'
import { computed, useTemplateRef, watch } from 'vue'

import { Button } from '@ui/button'

import { type KeyboardShortcut, useKeyboardShortcuts } from '../../lib/useKeyboardShortcuts'

const WHEEL_NAVIGATION_THRESHOLD_PX = 40

const props = withDefaults(
  defineProps<{
    items: readonly LightboxItem[]
    actions?: readonly LightboxAction[]
    shortcuts?: readonly KeyboardShortcut[]
  }>(),
  { actions: () => [], shortcuts: () => [] },
)

defineSlots<{
  default(props: { open: (key?: string) => void }): unknown
}>()

const lightboxOpen = defineModel<boolean>('open', { default: false })
const activeKey = defineModel<string | null>('activeKey', { default: null })
const content = useTemplateRef<HTMLElement>('content')
const itemKeys = computed(() => props.items.map((item) => item.key))
const currentIndex = computed(() =>
  Math.max(
    props.items.findIndex((item) => item.key === activeKey.value),
    0,
  ),
)
const currentItem = computed(() => props.items[currentIndex.value])

let wheelDelta = 0
let wheelDirection = 0

function openLightbox(key = activeKey.value ?? undefined) {
  const item = props.items.find((item) => item.key === key) ?? props.items[0]
  if (!item) return
  activeKey.value = item.key
  lightboxOpen.value = true
}

function closeLightbox() {
  lightboxOpen.value = false
}

function resetWheelNavigation() {
  wheelDelta = 0
  wheelDirection = 0
}

function selectAdjacentItem(offset: -1 | 1) {
  resetWheelNavigation()
  const next = props.items[currentIndex.value + offset]
  if (next) activeKey.value = next.key
}

function normalizedWheelDelta(event: WheelEvent) {
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) return event.deltaY * 16
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) return event.deltaY * window.innerHeight
  return event.deltaY
}

function handleWheel(event: WheelEvent) {
  if (!isActive() || event.deltaY === 0 || event.ctrlKey) return

  event.preventDefault()
  if (props.items.length <= 1) return

  const delta = normalizedWheelDelta(event)
  const direction = Math.sign(delta)
  if (direction !== wheelDirection) {
    wheelDelta = 0
    wheelDirection = direction
  }

  wheelDelta += delta
  if (Math.abs(wheelDelta) < WHEEL_NAVIGATION_THRESHOLD_PX) return

  selectAdjacentItem(wheelDelta < 0 ? -1 : 1)
}

const isActive = useKeyboardShortcuts(
  () => [
    { key: 'ArrowLeft', action: () => selectAdjacentItem(-1) },
    { key: 'ArrowRight', action: () => selectAdjacentItem(1) },
    ...props.shortcuts,
  ],
  content,
)

watch(
  [itemKeys, activeKey, lightboxOpen],
  () => {
    const first = props.items[0]
    if (!first) {
      activeKey.value = null
      closeLightbox()
      return
    }
    if (activeKey.value === null || !itemKeys.value.includes(activeKey.value)) {
      activeKey.value = first.key
    }
  },
  { immediate: true },
)

watch([activeKey, lightboxOpen, itemKeys], resetWheelNavigation)
</script>
<!-- TODO: 图片可缩放、更多信息 -->
<template>
  <DialogRoot v-model:open="lightboxOpen">
    <slot :open="openLightbox" />

    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-foreground/80 dark:bg-background/80" />
      <DialogContent
        class="fixed inset-0 z-50 overflow-hidden text-background outline-none dark:text-foreground"
        @open-auto-focus.prevent="content?.focus({ preventScroll: true })"
      >
        <DialogTitle class="sr-only">作品预览</DialogTitle>
        <DialogDescription class="sr-only">全屏查看当前作品</DialogDescription>
        <div
          ref="content"
          tabindex="-1"
          class="relative flex size-full items-center justify-center p-4 outline-none sm:p-8"
          @click.self="closeLightbox"
          @wheel="handleWheel"
        >
          <img
            v-if="currentItem"
            class="block h-auto max-h-full w-auto max-w-full object-contain"
            :src="currentItem.src"
            :alt="currentItem.alt"
            decoding="async"
            draggable="false"
          />
          <output
            class="absolute top-4 left-4 rounded-full bg-foreground/65 px-3 py-1 text-sm text-background tabular-nums sm:top-6 sm:left-6 dark:bg-background/65 dark:text-foreground"
          >
            {{ currentIndex + 1 }} / {{ items.length }}
          </output>
          <div
            v-if="currentItem && actions.length > 0"
            class="absolute top-4 right-4 flex items-center sm:top-6 sm:right-6"
          >
            <Button
              v-for="action in actions"
              :key="action.title"
              variant="ghost"
              size="icon"
              :title="action.title"
              class="rounded-none opacity-75 hover:bg-transparent hover:text-inherit hover:opacity-100"
              @click="currentItem && action.action(currentItem)"
            >
              <span class="size-6" :class="action.icon" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
