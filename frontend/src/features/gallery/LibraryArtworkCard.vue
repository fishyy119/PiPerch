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
  showTitle: boolean
  showAuthor: boolean
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

function handleCardClick(event: MouseEvent) {
  if (!props.selectionMode) return

  event.preventDefault()
  event.stopPropagation()
  emit('toggleSelection', props.artwork.artworkId)
}
</script>

<template>
  <ArtworkCard
    :class="{ 'cursor-pointer': selectionMode }"
    :title="artwork.title"
    :author-name="artwork.authorName"
    :page-count="artwork.pageCount"
    :thumbnail-url="thumbnailUrl"
    :target="target"
    :resolve-preview-url="resolvePreviewUrl"
    :selected="selected"
    :show-title="showTitle"
    :show-author="showAuthor"
    :show-page-preview="!selectionMode"
    @click.capture="handleCardClick"
  >
    <template v-if="selectionMode" #leading-action>
      <Checkbox
        :class="[
          'absolute top-2 left-2 z-10 size-5',
          'border-overlay-foreground/80 bg-overlay/55 shadow-sm backdrop-blur-sm transition',
        ]"
        :model-value="selected"
        @click.stop
        @update:model-value="emit('toggleSelection', artwork.artworkId)"
      />
    </template>

    <template #author>
      <button
        type="button"
        :class="[
          'block max-w-full cursor-pointer truncate text-left text-xs text-muted-foreground hover:text-primary',
          showTitle ? 'mt-0.5' : '',
        ]"
        @click="emit('filterAuthor', artwork.authorId)"
      >
        {{ artwork.authorName }}
      </button>
    </template>
  </ArtworkCard>
</template>
