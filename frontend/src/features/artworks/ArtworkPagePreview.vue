<script setup lang="ts">
import { ImageOff, LoaderCircle } from '@lucide/vue'
import { ref, watch } from 'vue'

import type { ArtworkPreviewUrlResolver } from '@/features/artworks/artwork-card'
import HoverCard from '@ui/HoverCard.vue'

const props = defineProps<{
  title: string
  pageCount: number
  resolveUrl: ArtworkPreviewUrlResolver
}>()

const previewPage = ref(0)
const previewOpen = ref(false)
const previewUrl = ref<string | null>(null)
const previewLoading = ref(false)
const previewImageLoaded = ref(false)
const previewImageFailed = ref(false)
const cachedUrls = new Map<number, string | null>()
let requestId = 0

watch(
  () => props.resolveUrl,
  () => {
    requestId += 1
    cachedUrls.clear()
    previewUrl.value = null
    previewLoading.value = false
    previewImageLoaded.value = false
    previewImageFailed.value = false
  },
)

function applyPreviewUrl(url: string | null) {
  if (previewUrl.value !== url) {
    previewImageLoaded.value = false
    previewImageFailed.value = false
  }
  previewUrl.value = url
}

async function showPreview(page: number) {
  const alreadyLoading = previewLoading.value && previewPage.value === page
  previewPage.value = page
  previewOpen.value = true
  if (alreadyLoading) return

  if (cachedUrls.has(page)) {
    requestId += 1
    previewLoading.value = false
    applyPreviewUrl(cachedUrls.get(page) ?? null)
    return
  }

  const currentRequest = ++requestId
  previewLoading.value = true
  applyPreviewUrl(null)
  try {
    const url = await props.resolveUrl(page)
    if (currentRequest !== requestId) return
    cachedUrls.set(page, url)
    applyPreviewUrl(url)
  } catch {
    if (currentRequest !== requestId) return
    previewImageFailed.value = true
  } finally {
    if (currentRequest === requestId) previewLoading.value = false
  }
}

function hidePreviewOnFocusOut(event: FocusEvent) {
  const container = event.currentTarget
  const nextTarget = event.relatedTarget
  if (!(container instanceof HTMLElement)) return
  if (nextTarget instanceof Node && container.contains(nextTarget)) return

  previewOpen.value = false
}
</script>

<template>
  <HoverCard
    v-model:open="previewOpen"
    :open-delay="0"
    :close-delay="75"
    :side-offset="12"
    content-class="relative overflow-hidden p-1"
  >
    <template #trigger>
      <div
        :class="[
          'absolute top-2 right-2 z-10',
          'max-w-[calc(100%-2rem)]',
          'grid grid-cols-[repeat(auto-fit,0.625rem)] justify-between gap-0.5 rounded-md p-1',
          'bg-overlay/55 shadow-sm backdrop-blur-sm transition',
          previewOpen
            ? 'opacity-100'
            : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100',
        ]"
        @focusout="hidePreviewOnFocusOut"
      >
        <button
          v-for="page in pageCount"
          :key="page"
          type="button"
          :class="[
            'size-2.5 rounded-full',
            'bg-overlay-foreground/70 ring-1 ring-overlay/20 transition',
            'hover:scale-125 hover:bg-primary focus-visible:scale-125 focus-visible:bg-primary',
            { 'bg-primary!': previewOpen && previewPage === page - 1 },
          ]"
          @pointerenter="showPreview(page - 1)"
          @focus="showPreview(page - 1)"
          @click.prevent.stop
        />
      </div>
    </template>

    <div class="relative grid min-h-40 min-w-72 place-items-center rounded-lg bg-muted">
      <img
        v-if="previewUrl && !previewImageFailed"
        :key="previewUrl"
        :class="[
          'block h-auto w-auto',
          'max-h-[min(720px,calc(var(--reka-hover-card-content-available-height)-0.5rem-2px))]',
          'max-w-[min(600px,max(320px,42vw),calc(var(--reka-hover-card-content-available-width)-0.5rem-2px))]',
          'rounded-lg object-contain transition-opacity',
          previewImageLoaded ? 'opacity-100' : 'opacity-0',
        ]"
        :src="previewUrl"
        :alt="`${title} 第 ${String(previewPage + 1)} 页快速预览`"
        @load="previewImageLoaded = true"
        @error="previewImageFailed = true"
      />
      <LoaderCircle
        v-if="previewLoading || (previewUrl && !previewImageLoaded && !previewImageFailed)"
        class="absolute inset-0 m-auto animate-spin text-muted-foreground"
        :size="28"
      />
      <ImageOff
        v-else-if="!previewUrl || previewImageFailed"
        class="absolute inset-0 m-auto text-muted-foreground"
        :size="28"
      />
    </div>
    <span
      class="absolute right-3 bottom-3 rounded-lg bg-overlay/65 px-2 py-1 text-xs text-overlay-foreground backdrop-blur-sm"
    >
      {{ previewPage + 1 }} / {{ pageCount }}
    </span>
  </HoverCard>
</template>
