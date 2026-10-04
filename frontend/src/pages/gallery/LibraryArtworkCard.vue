<script setup lang="ts">
import { Heart } from '@lucide/vue'
import { computed, ref } from 'vue'

import { usePreference } from '@/app/usePreference'
import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import { useGalleryFilters } from '@/features/gallery/gallery-filter'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import LibraryArtworkContextMenu from '@/pages/gallery/LibraryArtworkContextMenu.vue'
import ArtworkCard from '@/shared/components/artworks/ArtworkCard.vue'
import Checkbox from '@ui/Checkbox.vue'

const props = defineProps<{
  artwork: ArtworkSummary
  navigationArtworkIds: readonly number[]
}>()

const target = computed<ArtworkCardTarget>(() => ({
  kind: 'route',
  to: {
    path: `/artworks/${String(props.artwork.artworkId)}`,
    state: galleryNavigationRouteState(props.navigationArtworkIds),
  },
}))
const contextMenuOpen = ref(false)
const selection = useGallerySelectionStore()
const { update: updateFilters } = useGalleryFilters()
const showTitle = usePreference('gallery.showTitle')
const showAuthor = usePreference('gallery.showAuthor')
const showFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const thumbnailUrl = computed(() => `/api/artworks/${String(props.artwork.artworkId)}/thumbnail`)

function resolvePreviewUrl(pageIndex: number) {
  return props.artwork.artworkType === 'ugoira'
    ? `/api/artworks/${String(props.artwork.artworkId)}/cover`
    : `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(pageIndex)}`
}

function handleCardClick(event: MouseEvent) {
  if (!selection.enabled) return

  event.preventDefault()
  event.stopPropagation()
  selection.toggleArtwork(props.artwork.artworkId)
}
</script>

<template>
  <LibraryArtworkContextMenu v-model:open="contextMenuOpen" :artwork="artwork">
    <ArtworkCard
      :class="{ 'cursor-pointer': selection.enabled }"
      :title="artwork.title"
      :author-name="artwork.authorName"
      :page-count="artwork.pageCount"
      :thumbnail-url="thumbnailUrl"
      :target="target"
      :resolve-preview-url="resolvePreviewUrl"
      :selected="selection.isSelected(artwork.artworkId)"
      :show-title="showTitle"
      :show-author="showAuthor"
      :show-page-preview="!selection.enabled && !contextMenuOpen"
      @click.capture="handleCardClick"
    >
      <template
        v-if="selection.enabled || (artwork.isFavorite && showFavoriteIndicator)"
        #leading-action
      >
        <Checkbox
          v-if="selection.enabled"
          :class="[
            'absolute top-2 left-2 z-10 size-5',
            'border-overlay-foreground/80 bg-overlay/55 shadow-sm backdrop-blur-sm transition',
          ]"
          :model-value="selection.isSelected(artwork.artworkId)"
          @click.stop
          @update:model-value="selection.toggleArtwork(artwork.artworkId)"
        />
        <span
          v-else
          class="pointer-events-none absolute top-2 left-2 z-10 grid size-7 place-items-center rounded-full bg-overlay/60 text-white shadow-sm backdrop-blur-sm"
        >
          <Heart :size="16" fill="currentColor" />
        </span>
      </template>

      <template #author>
        <button
          type="button"
          :class="[
            'block max-w-full cursor-pointer truncate text-left text-xs text-muted-foreground hover:text-primary',
            showTitle ? 'mt-0.5' : '',
          ]"
          @click="updateFilters({ authorId: artwork.authorId })"
        >
          {{ artwork.authorName }}
        </button>
      </template>
    </ArtworkCard>
  </LibraryArtworkContextMenu>
</template>
