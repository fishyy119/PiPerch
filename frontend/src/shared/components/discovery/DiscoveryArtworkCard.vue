<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import { type DiscoveryItem, listArtworkPreviewUrls } from '@/features/discovery/discovery-api'
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
const target = computed<ArtworkCardTarget>(() => ({
  kind: 'external',
  href: `https://www.pixiv.net/artworks/${String(props.artwork.artworkId)}`,
}))

async function resolvePreviewUrl(pageIndex: number) {
  const urls = await queryClient.query({
    queryKey: ['discovery-artwork-preview', props.artwork.artworkId],
    queryFn: () => listArtworkPreviewUrls(props.artwork.artworkId),
    retry: false,
    staleTime: 'static',
  })
  return urls[pageIndex] ?? null
}

function handleCardClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Element) || target.closest('button')) return

  const link = target.closest('a')
  if (event.ctrlKey && link) return
  if (link) event.preventDefault()
  if (!props.artwork.inLibrary) emit('toggle', props.artwork)
}
</script>

<template>
  <ArtworkCard
    class="cursor-crosshair select-none"
    :data-selection-id="artwork.inLibrary ? undefined : artwork.artworkId"
    :title="artwork.title"
    :author-name="artwork.authorName"
    :page-count="artwork.pageCount"
    :thumbnail-url="artwork.thumbnailUrl"
    :target="target"
    :resolve-preview-url="resolvePreviewUrl"
    :selected="selected"
    :show-author="showAuthor"
    @click.capture="handleCardClick"
    @dragstart.capture.prevent
  >
    <template #trailing-action>
      <!-- TODO: 此状态不会动态同步 -->
      <span
        v-if="artwork.inLibrary"
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-success px-2 py-1 text-xs font-medium text-success-foreground shadow-sm"
      >
        已在图库
      </span>
    </template>
  </ArtworkCard>
</template>
