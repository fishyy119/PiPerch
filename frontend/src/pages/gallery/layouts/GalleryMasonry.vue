<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { type ArtworkSummary, listArtworkImages } from '@/features/artworks/artworks-api'
import { galleryMediaItems } from '@/features/gallery/gallery-media'
import { useGalleryMasonry } from '@/features/gallery/useGalleryMasonry'
import { artworkQueryKeys } from '@/features/library/library-query-cache'

import GalleryMasonryImage from '../components/GalleryMasonryImage.vue'

const props = defineProps<{
  artworks: readonly ArtworkSummary[]
}>()
const navigationArtworkIds = computed(() => props.artworks.map((artwork) => artwork.localArtworkId))
const imagesQuery = useQuery({
  queryKey: computed(() => artworkQueryKeys.images(navigationArtworkIds.value)),
  queryFn: ({ signal }) => listArtworkImages(navigationArtworkIds.value, signal),
  enabled: computed(() => navigationArtworkIds.value.length > 0),
})
const items = computed(() => galleryMediaItems(props.artworks, imagesQuery.data.value ?? []))
const root = ref<HTMLElement | null>(null)
const { visibleItems, totalHeight, columnWidth, gap, scrollMargin, focusedKey } = useGalleryMasonry(
  root,
  items,
)
const renderedItems = computed(() =>
  visibleItems.value.flatMap((position) => {
    const item = items.value[position.index]
    return item ? [{ item, position }] : []
  }),
)

function handleFocusOut(event: FocusEvent) {
  if (
    event.currentTarget instanceof HTMLElement &&
    event.relatedTarget instanceof Node &&
    event.currentTarget.contains(event.relatedTarget)
  )
    return
  focusedKey.value = null
}
</script>

<template>
  <div v-if="imagesQuery.isPending.value" class="py-20 text-center text-muted-foreground">
    正在读取图片…
  </div>
  <div v-else-if="imagesQuery.error.value" class="py-20 text-center text-destructive">
    {{ imagesQuery.error.value.message }}
  </div>
  <div
    v-else
    ref="root"
    class="relative"
    :style="{ height: `${String(totalHeight)}px`, overflowAnchor: 'none' }"
  >
    <div
      v-for="{ item, position } in renderedItems"
      :key="item.key"
      class="absolute top-0 left-0"
      :style="{
        width: `${String(columnWidth)}px`,
        transform: `translate(${String(position.lane * (columnWidth + gap))}px, ${String(position.start - scrollMargin)}px)`,
      }"
      @focusin="focusedKey = item.key"
      @focusout="handleFocusOut"
    >
      <GalleryMasonryImage :item="item" :navigation-artwork-ids="navigationArtworkIds" />
    </div>
  </div>
</template>
