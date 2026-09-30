<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { ArtworkSummary } from '@/features/gallery/gallery-api'
import Checkbox from '@ui/Checkbox.vue'
import HoverCard from '@ui/HoverCard.vue'
import SmartCropImage from '@ui/SmartCropImage.vue'

const props = defineProps<{
  artwork: ArtworkSummary
  selected: boolean
  selectionMode: boolean
}>()

const previewPage = ref(0)
const previewOpen = ref(false)

const emit = defineEmits<{
  toggleSelection: [artworkId: number]
  filterAuthor: [authorId: number]
}>()

function previewUrl(page: number) {
  return props.artwork.artworkType === 'ugoira'
    ? `/api/artworks/${String(props.artwork.artworkId)}/cover`
    : `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(page)}`
}

function showPreview(page: number) {
  previewPage.value = page
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
    <div
      class="relative aspect-square overflow-hidden rounded-xl bg-muted ring-primary transition"
      :class="selected ? 'ring-3' : 'ring-0'"
    >
      <RouterLink
        class="block size-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        :to="`/artworks/${String(artwork.artworkId)}`"
      >
        <SmartCropImage
          class="size-full object-cover transition duration-300 group-hover:scale-[1.025]"
          :src="`/api/artworks/${String(artwork.artworkId)}/thumbnail`"
          :alt="artwork.title"
          loading="lazy"
        />
      </RouterLink>

      <Checkbox
        :class="[
          'absolute top-2 left-2 z-10 size-5',
          'border-overlay-foreground/80 bg-overlay/55 shadow-sm backdrop-blur-sm transition',
          'sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100',
          { 'opacity-100!': selectionMode || selected },
        ]"
        :model-value="selected"
        @click.stop
        @update:model-value="emit('toggleSelection', artwork.artworkId)"
      />

      <HoverCard
        v-model:open="previewOpen"
        :open-delay="0"
        :close-delay="75"
        :side-offset="12"
        content-class="relative overflow-hidden p-1"
      >
        <template #trigger="{ open }">
          <div
            :class="[
              'absolute top-2 right-2 z-10 max-w-[calc(100%-3rem)]',
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
                { 'bg-primary!': open && previewPage === page - 1 },
              ]"
              @pointerenter="showPreview(page - 1)"
              @focus="showPreview(page - 1)"
              @click.prevent.stop
            />
          </div>
        </template>

        <img
          :class="[
            'block h-auto w-auto',
            'max-h-[min(720px,calc(var(--reka-hover-card-content-available-height)-0.5rem-2px))]',
            'max-w-[min(600px,max(320px,42vw),calc(var(--reka-hover-card-content-available-width)-0.5rem-2px))]',
            'rounded-lg object-contain',
          ]"
          :src="previewUrl(previewPage)"
          :alt="`${artwork.title} 第 ${String(previewPage + 1)} 页快速预览`"
        />
        <span
          class="absolute right-3 bottom-3 rounded-lg bg-overlay/65 px-2 py-1 text-xs text-overlay-foreground backdrop-blur-sm"
        >
          {{ previewPage + 1 }} / {{ artwork.pageCount }}
        </span>
      </HoverCard>
    </div>

    <div class="pt-2.5">
      <RouterLink
        class="block truncate text-sm font-semibold hover:text-primary"
        :to="`/artworks/${String(artwork.artworkId)}`"
      >
        {{ artwork.title }}
      </RouterLink>
      <button
        type="button"
        class="app-muted mt-0.5 block max-w-full truncate text-left text-xs hover:text-primary"
        @click="emit('filterAuthor', artwork.authorId)"
      >
        {{ artwork.authorName }}
      </button>
    </div>
  </article>
</template>
