<script setup lang="ts">
import { ImageDown, ImageMinus, ImageOff, ImagePlus, LoaderCircle } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import { type DiscoveryItem, listArtworkPreviewUrls } from '@/features/downloads/download-api'
import HoverCard from '@ui/HoverCard.vue'
import SmartCropImage from '@ui/SmartCropImage.vue'

const props = defineProps<{
  artwork: DiscoveryItem
  selected: boolean
}>()

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
}>()

const previewPage = ref(0)
const previewOpen = ref(false)
const previewRequested = ref(false)
const previewImageLoaded = ref(false)
const previewImageFailed = ref(false)
const thumbnailFailed = ref(false)

const previewQuery = useQuery({
  queryKey: computed(() => ['discovery-artwork-preview', props.artwork.artworkId]),
  queryFn: () => listArtworkPreviewUrls(props.artwork.artworkId),
  enabled: computed(() => previewRequested.value),
  retry: false,
  staleTime: Number.POSITIVE_INFINITY,
})

const previewUrl = computed(() => previewQuery.data.value?.[previewPage.value] ?? null)

watch(previewUrl, () => {
  previewImageLoaded.value = false
  previewImageFailed.value = false
})

function pixivArtworkUrl() {
  return `https://www.pixiv.net/artworks/${String(props.artwork.artworkId)}`
}

function showPreview(page: number) {
  previewPage.value = page
  previewRequested.value = true
  previewOpen.value = true
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
  <article class="group min-w-0">
    <div class="relative aspect-square overflow-hidden rounded-xl bg-muted">
      <a
        class="block size-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        :href="pixivArtworkUrl()"
        target="_blank"
        rel="noreferrer"
      >
        <SmartCropImage
          v-if="artwork.thumbnailUrl && !thumbnailFailed"
          class="size-full object-cover transition duration-300 group-hover:scale-[1.025]"
          :src="artwork.thumbnailUrl"
          :alt="artwork.title"
          loading="lazy"
          @error="thumbnailFailed = true"
        />
        <ImageOff v-else class="app-muted absolute inset-0 m-auto" :size="28" />
      </a>

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
              'absolute top-2 right-2 z-10 max-w-[calc(100%-1rem)]',
              'flex flex-wrap justify-end gap-0.5 rounded-full p-1',
              'bg-overlay/55 opacity-0 shadow-sm backdrop-blur-sm transition',
              'group-focus-within:opacity-100 group-hover:opacity-100',
            ]"
            @focusout="hidePreviewOnFocusOut"
          >
            <button
              v-for="page in artwork.pageCount"
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
            :alt="`${artwork.title} 第 ${String(previewPage + 1)} 页快速预览`"
            @load="previewImageLoaded = true"
            @error="previewImageFailed = true"
          />
          <LoaderCircle
            v-if="
              previewQuery.isFetching.value ||
              (previewUrl && !previewImageLoaded && !previewImageFailed)
            "
            class="absolute inset-0 m-auto animate-spin text-muted-foreground"
            :size="28"
          />
          <ImageOff
            v-else-if="!previewUrl || previewImageFailed"
            class="app-muted absolute inset-0 m-auto"
            :size="28"
          />
        </div>
        <span
          class="absolute right-3 bottom-3 rounded-lg bg-overlay/65 px-2 py-1 text-xs text-overlay-foreground backdrop-blur-sm"
        >
          {{ previewPage + 1 }} / {{ artwork.pageCount }}
        </span>
      </HoverCard>

      <button
        v-if="!artwork.inLibrary"
        type="button"
        :class="[
          'group/queue absolute right-2 bottom-2 z-10 inline-flex size-10 items-center justify-center rounded-xl',
          'cursor-pointer shadow-sm ring-1 ring-transparent backdrop-blur-sm transition',
          'opacity-100 sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100',
          selected
            ? 'bg-primary/15 text-primary ring-primary/25 sm:opacity-100'
            : 'bg-overlay/65 text-overlay-foreground',
          selected
            ? 'hover:bg-destructive/10 hover:text-destructive hover:ring-destructive/25 focus-visible:bg-destructive/10 focus-visible:text-destructive focus-visible:ring-destructive/25'
            : 'hover:bg-primary/15 hover:text-primary hover:ring-primary/25 focus-visible:bg-primary/15 focus-visible:text-primary focus-visible:ring-primary/25',
        ]"
        :title="selected ? '从待提交队列移除' : '加入待提交队列'"
        @click.prevent.stop="emit('toggle', artwork)"
      >
        <ImagePlus v-if="!selected" :size="20" />
        <ImageDown
          v-else
          class="group-hover/queue:hidden group-focus-visible/queue:hidden"
          :size="20"
        />
        <ImageMinus
          v-if="selected"
          class="hidden group-hover/queue:block group-focus-visible/queue:block"
          :size="20"
        />
      </button>
      <!-- TODO: 此状态不会动态同步 -->
      <span
        v-else
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-success px-2 py-1 text-xs font-medium text-success-foreground shadow-sm"
      >
        已在图库
      </span>
    </div>

    <div class="pt-2.5">
      <a
        class="block truncate text-sm font-semibold hover:text-primary"
        :href="pixivArtworkUrl()"
        target="_blank"
        rel="noreferrer"
      >
        {{ artwork.title }}
      </a>
      <span class="app-muted mt-0.5 block truncate text-xs">
        {{ artwork.authorName }}
      </span>
    </div>
  </article>
</template>
