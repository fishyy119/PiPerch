<script setup lang="ts">
import { Heart } from '@lucide/vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { usePreference } from '@/app/usePreference'
import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import { replaceFavoriteState } from '@/features/favorites/favorites-api'
import { useGalleryFilters } from '@/features/gallery/gallery-filter'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import { invalidateArtworkData } from '@/features/library/library-query-cache'
import LibraryArtworkContextMenu from '@/pages/gallery/LibraryArtworkContextMenu.vue'
import ArtworkCard from '@/shared/components/artworks/ArtworkCard.vue'
import { errorMessage } from '@/shared/errors'
import Checkbox from '@ui/Checkbox.vue'
import { toast } from '@ui/toast'

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
const queryClient = useQueryClient()
const selection = useGallerySelectionStore()
const { update: updateFilters } = useGalleryFilters()
const showTitle = usePreference('gallery.showTitle')
const showAuthor = usePreference('gallery.showAuthor')
const showFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const thumbnailUrl = computed(() => `/api/artworks/${String(props.artwork.artworkId)}/thumbnail`)
const favoriteMutation = useMutation({
  mutationFn: () => replaceFavoriteState(props.artwork.artworkId, !props.artwork.isFavorite),
  onSuccess: async (favoriteState) => {
    await invalidateArtworkData(queryClient)
    toast.success(favoriteState.isFavorite ? '已收藏' : '已取消收藏')
  },
  onError: (error) => {
    toast.error('更新收藏失败', { description: errorMessage(error) })
  },
})

function resolvePreviewUrl(pageIndex: number) {
  return props.artwork.artworkType === 'ugoira'
    ? `/api/artworks/${String(props.artwork.artworkId)}/cover`
    : `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(pageIndex)}`
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
  selection.toggleArtwork(props.artwork.artworkId)
}

function handleCardDragStart(event: DragEvent) {
  // 避免原生图片或链接拖拽吞掉批量选择的点击事件。
  if (selection.enabled) event.preventDefault()
}
</script>

<template>
  <LibraryArtworkContextMenu v-model:open="contextMenuOpen" :artwork="artwork">
    <ArtworkCard
      :class="{ 'cursor-crosshair': selection.enabled }"
      :data-gallery-artwork-id="artwork.artworkId"
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
      @dragstart.capture="handleCardDragStart"
    >
      <template v-if="selection.enabled || showFavoriteIndicator" #leading-action>
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
        <button
          type="button"
          data-artwork-card-favorite
          :class="[
            'absolute bottom-2 left-2 z-10 grid size-8 cursor-pointer place-items-center',
            'drop-shadow-sm transition hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
            'disabled:cursor-wait disabled:opacity-60',
            artwork.isFavorite ? 'text-foreground' : 'text-foreground/60 hover:text-foreground',
          ]"
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
