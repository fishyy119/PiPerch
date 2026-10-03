<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getArtwork } from '@/features/gallery/gallery-api'
import {
  galleryNavigationRouteState,
  type GalleryNavigationState,
  parseGalleryNavigationState,
} from '@/features/gallery/gallery-navigation'
import ArtworkDescriptionSection from '@/pages/artworks/ArtworkDescriptionSection.vue'
import ArtworkInfoSidebar from '@/pages/artworks/ArtworkInfoSidebar.vue'
import ArtworkMediaSection from '@/pages/artworks/ArtworkMediaSection.vue'
import RelatedArtworksSection from '@/pages/artworks/RelatedArtworksSection.vue'
import { usePageKeyboardShortcuts } from '@/shared/lib/usePageKeyboardShortcuts'

const route = useRoute()
const router = useRouter()
const artworkId = computed(() => Number(route.params.artworkId))
const galleryNavigation = ref<GalleryNavigationState | null>(
  parseGalleryNavigationState(router.options.history.state),
)

const artworkQuery = useQuery({
  queryKey: computed(() => ['artwork', artworkId.value]),
  queryFn: () => getArtwork(artworkId.value),
  placeholderData: (previousData) => previousData,
})

watch(artworkId, (currentArtworkId) => {
  const navigation = parseGalleryNavigationState(router.options.history.state)
  galleryNavigation.value = navigation?.artworkIds.includes(currentArtworkId) ? navigation : null
})

function selectAdjacentArtwork(offset: -1 | 1) {
  const navigation = galleryNavigation.value
  if (navigation === null) return

  const currentIndex = navigation.artworkIds.indexOf(artworkId.value)
  if (currentIndex < 0) return

  const nextArtworkId = navigation.artworkIds[currentIndex + offset]
  if (nextArtworkId === undefined) return

  void router
    .replace({
      path: `/artworks/${String(nextArtworkId)}`,
      state: galleryNavigationRouteState(navigation.artworkIds),
    })
    .then(() => window.scrollTo({ top: 0 }))
}

usePageKeyboardShortcuts(
  (event) => {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
    const navigation = galleryNavigation.value
    if (!navigation?.artworkIds.includes(artworkId.value)) return

    event.preventDefault()
    selectAdjacentArtwork(event.key === 'ArrowUp' ? -1 : 1)
  },
  { allowOverlay: (overlay) => overlay.classList.contains('artwork-lightbox') },
)
</script>

<template>
  <div v-if="artworkQuery.isPending.value" class="py-24 text-center text-muted-foreground">
    正在读取作品…
  </div>
  <div v-else-if="artworkQuery.error.value" class="py-24 text-center text-destructive">
    {{ artworkQuery.error.value.message }}
  </div>
  <article v-else-if="artworkQuery.data.value">
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="min-w-0 space-y-5">
        <ArtworkMediaSection :artwork="artworkQuery.data.value" />
        <ArtworkDescriptionSection :artwork="artworkQuery.data.value" />
        <RelatedArtworksSection :artwork-id="artworkId" />
      </div>

      <ArtworkInfoSidebar :artwork="artworkQuery.data.value" />
    </div>
  </article>
</template>
