<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import {
  type ArtworkCardTarget,
  type ArtworkPreviewUrlResolver,
  localArtworkPreviewUrl,
} from '@/features/artworks/artwork-card'
import { artworkOriginalUrl, artworkReferenceKey } from '@/features/artworks/artwork-source'
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
  library.isInLibrary(props.artwork.remoteId, props.artwork.inLibrary, props.artwork.source),
)
const localId = computed(() =>
  library.localId(props.artwork.remoteId, props.artwork.source, props.artwork.localArtworkId),
)
const thumbnailUrl = computed(() =>
  inLibrary.value && localId.value !== null
    ? `/api/artworks/${String(localId.value)}/thumbnail`
    : props.artwork.thumbnailUrl,
)
const target = computed<ArtworkCardTarget>(() => ({
  kind: 'external',
  href: artworkOriginalUrl(props.artwork),
}))

const resolvePreviewUrl = computed<ArtworkPreviewUrlResolver>(() => {
  const { remoteId, artworkType, source, authorId } = props.artwork
  if (inLibrary.value && localId.value !== null) {
    const id = localId.value
    return (pageIndex) => localArtworkPreviewUrl(id, artworkType, pageIndex)
  }

  return async (pageIndex) => {
    const urls = await queryClient.query({
      queryKey: ['discovery-artwork-preview', source, remoteId, authorId],
      queryFn: () => listArtworkPreviewUrls(props.artwork),
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
    :data-selection-id="
      inLibrary ? undefined : artworkReferenceKey(artwork.source, artwork.remoteId)
    "
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
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground shadow-sm"
      >
        已在图库
      </span>
      <span
        v-else-if="artwork.previewOnly"
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-foreground/75 px-2 py-1 text-xs font-medium text-background shadow-sm dark:bg-background/75 dark:text-foreground"
      >
        仅预览图
      </span>
    </template>
  </ArtworkCard>
</template>
