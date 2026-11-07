<script setup lang="ts">
import { Heart } from '@lucide/vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { usePreference } from '@/app/usePreference'
import { type ArtworkCardTarget, localArtworkPreviewUrl } from '@/features/artworks/artwork-card'
import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import { notifyFavoriteUpdate } from '@/features/favorites/favorite-feedback'
import { replaceFavoriteState } from '@/features/favorites/favorites-api'
import { useGalleryFilters } from '@/features/gallery/gallery-filter'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import { invalidateArtworkData } from '@/features/library/library-query-cache'
import LibraryArtworkContextMenu from '@/pages/gallery/LibraryArtworkContextMenu.vue'
import ArtworkCard from '@/shared/components/artworks/ArtworkCard.vue'
import { errorMessage } from '@/shared/errors'
import { Checkbox } from '@ui/checkbox'
import { cn } from '@ui/cn'
import { toast } from '@ui/toast'

const props = defineProps<{
  artwork: ArtworkSummary
  navigationArtworkIds: readonly number[]
}>()

const target = computed<ArtworkCardTarget>(() => ({
  kind: 'route',
  to: {
    path: `/artworks/${String(props.artwork.localArtworkId)}`,
    state: galleryNavigationRouteState(props.navigationArtworkIds),
  },
}))
const contextMenuOpen = ref(false)
const queryClient = useQueryClient()
const selection = useGallerySelectionStore()
const { update: updateFilters } = useGalleryFilters()
const showTitle = usePreference('gallery.showTitle')
const showAuthor = usePreference('gallery.showAuthor')
const showFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const thumbnailUrl = computed(
  () => `/api/artworks/${String(props.artwork.localArtworkId)}/thumbnail`,
)
const favoriteMutation = useMutation({
  mutationFn: () => replaceFavoriteState(props.artwork.localArtworkId, !props.artwork.isFavorite),
  onSuccess: async (favoriteState) => {
    await invalidateArtworkData(queryClient)
    notifyFavoriteUpdate(favoriteState, props.artwork.source)
  },
  onError: (error) => {
    toast.error('更新收藏失败', { description: errorMessage(error) })
  },
})

function resolvePreviewUrl(pageIndex: number) {
  return localArtworkPreviewUrl(props.artwork.localArtworkId, props.artwork.artworkType, pageIndex)
}

function handleCardClick(event: MouseEvent) {
  if (!selection.enabled) return
  if (
    event.target instanceof Element &&
    event.target.closest('[data-artwork-card-favorite]') !== null
  ) {
    return
  }

  event.preventDefault()
  event.stopPropagation()
  selection.toggleArtwork(props.artwork.localArtworkId)
}

function handleCardDragStart(event: DragEvent) {
  // 避免原生图片或链接拖拽吞掉批量选择的点击事件。
  if (selection.enabled) event.preventDefault()
}
</script>

<template>
  <LibraryArtworkContextMenu v-model:open="contextMenuOpen" :artwork="artwork">
    <ArtworkCard
      :data-selection-id="artwork.localArtworkId"
      :title="artwork.title"
      :author-name="artwork.authorName"
      :page-count="artwork.pageCount"
      :thumbnail-url="thumbnailUrl"
      :target="target"
      :resolve-preview-url="resolvePreviewUrl"
      :selected="selection.isSelected(artwork.localArtworkId)"
      :show-title="showTitle"
      :show-author="showAuthor"
      :show-page-preview="!selection.enabled && !contextMenuOpen"
      @click.capture="handleCardClick"
      @dragstart.capture="handleCardDragStart"
    >
      <template v-if="selection.enabled || showFavoriteIndicator" #leading-action>
        <Checkbox
          v-if="selection.enabled"
          :class="
            cn(
              'absolute top-2 left-2 z-10 size-5',
              'border-overlay-foreground/80 bg-overlay/55 shadow-sm backdrop-blur-sm transition',
            )
          "
          :model-value="selection.isSelected(artwork.localArtworkId)"
          @click.stop
          @update:model-value="selection.toggleArtwork(artwork.localArtworkId)"
        />
        <button
          type="button"
          data-artwork-card-favorite
          :class="
            cn(
              'absolute bottom-2 left-2 z-10 grid size-8 cursor-pointer place-items-center',
              'drop-shadow-sm transition hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
              'disabled:cursor-wait disabled:opacity-60',
              artwork.isFavorite ? 'text-foreground' : 'text-foreground/60 hover:text-foreground',
            )
          "
          :title="artwork.isFavorite ? '取消收藏' : '收藏'"
          :disabled="favoriteMutation.isPending.value"
          @click.prevent.stop="favoriteMutation.mutate()"
        >
          <Heart
            :size="28"
            :class="artwork.isFavorite ? 'fill-red-500 dark:fill-red-400' : 'fill-card'"
          />
        </button>
      </template>

      <template #author="{ selected }">
        <button
          type="button"
          :class="
            cn(
              'block max-w-full cursor-pointer truncate text-left text-xs transition-colors',
              selected ? 'text-primary-foreground' : 'text-muted-foreground hover:text-primary',
              showTitle ? 'mt-0.5' : '',
            )
          "
          @click="updateFilters({ authorId: artwork.authorId })"
        >
          {{ artwork.authorName }}
        </button>
      </template>
    </ArtworkCard>
  </LibraryArtworkContextMenu>
</template>
