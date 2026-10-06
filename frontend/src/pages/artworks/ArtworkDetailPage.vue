<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { type ArtworkDetail, getArtwork } from '@/features/artworks/artworks-api'
import {
  galleryNavigationRouteState,
  type GalleryNavigationState,
  parseGalleryNavigationState,
} from '@/features/gallery/gallery-navigation'
import { artworkQueryKeys } from '@/features/library/library-query-cache'
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
  queryKey: computed(() => artworkQueryKeys.detail(artworkId.value)),
  queryFn: () => getArtwork(artworkId.value),
  // 保留上一份数据以避免中间加载态高度坍缩；遮罩层负责阻止旧内容被操作。
  placeholderData: (previousData) => previousData,
})
const retainedMediaArtwork = shallowRef<ArtworkDetail | null>(null)

watch(
  () => artworkQuery.data.value,
  (artwork) => {
    if (artwork !== undefined) retainedMediaArtwork.value = artwork
  },
  { immediate: true },
)

watch(
  () => artworkQuery.error.value,
  (error) => {
    if (error !== null) retainedMediaArtwork.value = null
  },
)

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
  <article v-if="retainedMediaArtwork" class="relative">
    <div
      v-if="artworkQuery.isPlaceholderData.value"
      class="absolute inset-0 z-10 cursor-progress"
    />
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="min-w-0 space-y-5">
        <!-- 查询下一件作品时保留组件实例，使 Teleport 中已打开的 Lightbox 不被销毁。 -->
        <div v-show="artworkQuery.data.value !== undefined">
          <ArtworkMediaSection :artwork="retainedMediaArtwork" />
        </div>
        <template v-if="artworkQuery.data.value">
          <ArtworkDescriptionSection :artwork="artworkQuery.data.value" />
          <RelatedArtworksSection :artwork-id="artworkId" />
        </template>
      </div>

      <ArtworkInfoSidebar v-if="artworkQuery.data.value" :artwork="artworkQuery.data.value" />
    </div>
  </article>
</template>
