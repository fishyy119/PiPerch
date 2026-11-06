<script setup lang="ts">
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { type ArtworkDetail, getArtwork } from '@/features/artworks/artworks-api'
import { getUserProfile, userProfileKey } from '@/features/authors/author-api'
import {
  galleryNavigationRouteState,
  type GalleryNavigationState,
  parseGalleryNavigationState,
} from '@/features/gallery/gallery-navigation'
import { artworkQueryKeys } from '@/features/library/library-query-cache'
import ArtworkDescriptionSection from '@/pages/artworks/ArtworkDescriptionSection.vue'
import ArtworkInfoSidebar from '@/pages/artworks/ArtworkInfoSidebar.vue'
import ArtworkMediaSection from '@/pages/artworks/ArtworkMediaSection.vue'
import RecommendedArtworksSection from '@/pages/artworks/RecommendedArtworksSection.vue'
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
  placeholderData: keepPreviousData,
})
// 旧作品只用于显示，依赖查询始终以当前作品的真实数据作为来源。
const currentArtwork = computed(() =>
  !artworkQuery.isPlaceholderData.value && artworkQuery.data.value?.artworkId === artworkId.value
    ? artworkQuery.data.value
    : undefined,
)
const displayedArtwork = shallowRef<ArtworkDetail | null>(null)

watch(
  () => artworkQuery.data.value,
  (artwork) => {
    if (artwork !== undefined) displayedArtwork.value = artwork
  },
  { immediate: true },
)
watch(
  () => artworkQuery.error.value,
  (error) => {
    if (error !== null) displayedArtwork.value = null
  },
)

const authorProfileQuery = useQuery({
  queryKey: computed(() => userProfileKey(currentArtwork.value?.authorId)),
  queryFn: ({ queryKey }) => {
    const authorId = queryKey[1]
    if (authorId === undefined) throw new Error('当前作品的作者尚未就绪。')
    return getUserProfile(authorId)
  },
  enabled: computed(() => currentArtwork.value !== undefined),
  placeholderData: keepPreviousData,
})
const authorProfile = computed(() => {
  const pending = currentArtwork.value === undefined || authorProfileQuery.isPlaceholderData.value
  return {
    current: pending ? undefined : authorProfileQuery.data.value,
    displayed: authorProfileQuery.data.value,
    status: pending ? 'pending' : authorProfileQuery.status.value,
  } as const
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
  <article v-if="displayedArtwork" class="relative">
    <div
      v-if="artworkQuery.isPlaceholderData.value"
      class="absolute inset-0 z-10 cursor-progress"
    />
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="min-w-0 space-y-5">
        <!-- 查询下一件作品时保留组件实例，使 Teleport 中已打开的 Lightbox 不被销毁。 -->
        <div v-show="artworkQuery.data.value !== undefined">
          <ArtworkMediaSection :artwork="displayedArtwork" />
        </div>
        <template v-if="artworkQuery.data.value">
          <ArtworkDescriptionSection :artwork="artworkQuery.data.value" />
          <RelatedArtworksSection :artwork-id="artworkId" />
          <RecommendedArtworksSection :artwork-id="artworkId" />
        </template>
      </div>

      <ArtworkInfoSidebar
        v-if="artworkQuery.data.value"
        :artwork="artworkQuery.data.value"
        :author-profile="authorProfile"
      />
    </div>
  </article>
</template>
