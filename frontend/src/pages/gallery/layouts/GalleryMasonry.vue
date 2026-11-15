<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { artworkMediaUrl } from '@/features/artworks/artwork'
import { type ArtworkSummary, listArtworkImages } from '@/features/artworks/artworks-api'
import { galleryMediaItems } from '@/features/gallery/gallery-media'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import { useGalleryMasonry } from '@/features/gallery/useGalleryMasonry'
import { artworkQueryKeys } from '@/features/library/library-query-cache'
import { type LightboxAction, LightboxGallery, type LightboxItem } from '@ui/lightbox-gallery'

import GalleryMasonryImage from '../components/GalleryMasonryImage.vue'

const props = defineProps<{
  artworks: readonly ArtworkSummary[]
}>()
const router = useRouter()
const artworkIds = computed(() => props.artworks.map((artwork) => artwork.localArtworkId))
const imagesQuery = useQuery({
  queryKey: computed(() => artworkQueryKeys.images(artworkIds.value)),
  queryFn: ({ signal }) => listArtworkImages(artworkIds.value, signal),
  enabled: computed(() => artworkIds.value.length > 0),
})
const items = computed(() => galleryMediaItems(props.artworks, imagesQuery.data.value ?? []))
const lightboxItems = computed(() =>
  items.value.map((item) => ({
    key: item.key,
    src: artworkMediaUrl(item.media.artworkId, item.artwork.artworkType, item.media.pageIndex ?? 0),
    alt: item.artwork.title,
  })),
)
const lightboxActions: readonly LightboxAction[] = [
  { title: '查看作品详情', icon: 'icon-[mdi--information]', action: openArtworkDetail },
]
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

function openArtworkDetail({ key }: LightboxItem) {
  const item = items.value.find((item) => item.key === key)
  if (!item) return
  void router
    .push({
      path: `/artworks/${String(item.artwork.localArtworkId)}`,
      state: galleryNavigationRouteState(artworkIds.value),
    })
    .then(() => window.scrollTo({ top: 0 }))
}
</script>

<template>
  <div v-if="imagesQuery.isPending.value" class="py-20 text-center text-muted-foreground">
    正在读取图片…
  </div>
  <div v-else-if="imagesQuery.error.value" class="py-20 text-center text-destructive">
    {{ imagesQuery.error.value.message }}
  </div>
  <LightboxGallery v-else v-slot="{ open }" :items="lightboxItems" :actions="lightboxActions">
    <div
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
        <GalleryMasonryImage :item="item" @open="open(item.key)" />
      </div>
    </div>
  </LightboxGallery>
</template>
