<script setup lang="ts">
import { computed, ref } from 'vue'

import { artworkMediaUrl } from '@/features/artworks/artwork'
import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import ArtworkCard, { type ArtworkCardTarget } from '@/shared/components/artworks/ArtworkCard.vue'
import LibraryArtworkContextMenu from '@/shared/components/artworks/LibraryArtworkContextMenu.vue'

const props = defineProps<{ artwork: ArtworkSummary }>()

const contextMenuOpen = ref(false)
const target = computed<ArtworkCardTarget>(() => ({
  kind: 'route',
  to: `/artworks/${String(props.artwork.localArtworkId)}`,
}))

function resolvePreviewUrl(pageIndex: number) {
  return artworkMediaUrl(props.artwork.localArtworkId, props.artwork.artworkType, pageIndex)
}
</script>

<template>
  <LibraryArtworkContextMenu v-model:open="contextMenuOpen" :artwork="artwork">
    <ArtworkCard
      :title="artwork.title"
      :author-name="artwork.authorName"
      :page-count="artwork.pageCount"
      :thumbnail-url="`/api/artworks/${String(artwork.localArtworkId)}/thumbnail`"
      :target="target"
      :resolve-preview-url="resolvePreviewUrl"
      :show-title="false"
      :show-author="false"
      :show-page-preview="!contextMenuOpen"
    />
  </LibraryArtworkContextMenu>
</template>
