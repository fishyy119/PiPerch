<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import {
  type ArtworkCardTarget,
  type ArtworkPreviewUrlResolver,
  localArtworkPreviewUrl,
} from '@/features/artworks/artwork-card'
import { type DiscoveryItem, listArtworkPreviewUrls } from '@/features/discovery/discovery-api'
import { useLibraryMembershipStore } from '@/features/library/library-membership'
import ArtworkCard from '@/shared/components/artworks/ArtworkCard.vue'

const props = withDefaults(
  defineProps<{
    artwork: DiscoveryItem
    selected: boolean
    showAuthor?: boolean
  }>(),
  { showAuthor: true },
)

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
}>()

const queryClient = useQueryClient()
const library = useLibraryMembershipStore()
const inLibrary = computed(() =>
  library.isInLibrary(props.artwork.artworkId, props.artwork.inLibrary),
)
const thumbnailUrl = computed(() =>
  inLibrary.value
    ? `/api/artworks/${String(props.artwork.artworkId)}/thumbnail`
    : props.artwork.thumbnailUrl,
)
const target = computed<ArtworkCardTarget>(() => ({
  kind: 'external',
  href: `https://www.pixiv.net/artworks/${String(props.artwork.artworkId)}`,
}))

const resolvePreviewUrl = computed<ArtworkPreviewUrlResolver>(() => {
  const { artworkId, artworkType } = props.artwork
  if (inLibrary.value) {
    return (pageIndex) => localArtworkPreviewUrl(artworkId, artworkType, pageIndex)
  }

  return async (pageIndex) => {
    const urls = await queryClient.query({
      queryKey: ['discovery-artwork-preview', artworkId],
      queryFn: () => listArtworkPreviewUrls(artworkId),
      retry: false,
      staleTime: 'static',
    })
    return urls[pageIndex] ?? null
  }
})

function handleCardClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Element) || target.closest('button')) return

  const link = target.closest('a')
  if (event.ctrlKey && link) return
  if (link) event.preventDefault()
  if (!inLibrary.value) emit('toggle', props.artwork)
}
</script>

<template>
  <ArtworkCard
    class="select-none"
    :data-selection-id="inLibrary ? undefined : artwork.artworkId"
    :title="artwork.title"
    :author-name="artwork.authorName"
    :page-count="artwork.pageCount"
    :thumbnail-url="thumbnailUrl"
    :target="target"
    :resolve-preview-url="resolvePreviewUrl"
    :selected="selected"
    :show-author="showAuthor"
    @click.capture="handleCardClick"
    @dragstart.capture.prevent
  >
    <template #trailing-action>
      <span
        v-if="inLibrary"
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-success px-2 py-1 text-xs font-medium text-success-foreground shadow-sm"
      >
        已在图库
      </span>
    </template>
  </ArtworkCard>
</template>
