<script setup lang="ts">
import { computed } from 'vue'

import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import ArtworkCard from '@/features/artworks/ArtworkCard.vue'
import type { ArtworkSummary } from '@/features/gallery/gallery-api'
import Checkbox from '@ui/Checkbox.vue'

const props = defineProps<{
  artwork: ArtworkSummary
  selected: boolean
  selectionMode: boolean
}>()

const emit = defineEmits<{
  toggleSelection: [artworkId: number]
  filterAuthor: [authorId: number]
}>()

const target = computed<ArtworkCardTarget>(() => ({
  kind: 'route',
  to: `/artworks/${String(props.artwork.artworkId)}`,
}))
const thumbnailUrl = computed(() => `/api/artworks/${String(props.artwork.artworkId)}/thumbnail`)

function resolvePreviewUrl(pageIndex: number) {
  return props.artwork.artworkType === 'ugoira'
    ? `/api/artworks/${String(props.artwork.artworkId)}/cover`
    : `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(pageIndex)}`
}
</script>

<template>
  <ArtworkCard
    :title="artwork.title"
    :author-name="artwork.authorName"
    :page-count="artwork.pageCount"
    :thumbnail-url="thumbnailUrl"
    :target="target"
    :resolve-preview-url="resolvePreviewUrl"
    :selected="selected"
  >
    <template #leading-action>
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
    </template>

    <template #author>
      <button
        type="button"
        class="app-muted mt-0.5 block max-w-full truncate text-left text-xs hover:text-primary"
        @click="emit('filterAuthor', artwork.authorId)"
      >
        {{ artwork.authorName }}
      </button>
    </template>
  </ArtworkCard>
</template>
