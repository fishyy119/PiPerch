<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { usePreference } from '@/app/usePreference'
import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import { useMarqueeSelection } from '@/shared/lib/useMarqueeSelection'

import LibraryArtworkCard from '../components/LibraryArtworkCard.vue'

const props = defineProps<{
  artworks: readonly ArtworkSummary[]
}>()
const cardWidth = usePreference('gallery.cardWidth')
const root = ref<HTMLElement | null>(null)
const selection = useGallerySelectionStore()
const navigationArtworkIds = computed(() => props.artworks.map((artwork) => artwork.localArtworkId))
const marquee = useMarqueeSelection(root, {
  enabled: () => selection.enabled,
  selectedItems: () => selection.selectedIds,
  setSelectedItems: selection.setSelected,
  getKey: (id) => String(id),
  resolveItem: (element) => {
    const id = Number(element.dataset.selectionId)
    return Number.isSafeInteger(id) && id > 0 ? id : undefined
  },
})
watch(() => props.artworks, marquee.reset)
</script>

<template>
  <div
    ref="root"
    class="gallery-grid"
    :class="{ 'select-none': selection.enabled }"
    :style="{ '--gallery-card-width': `${String(cardWidth)}px` }"
    @click.capture="marquee.handleClick"
  >
    <LibraryArtworkCard
      v-for="artwork in artworks"
      :key="artwork.localArtworkId"
      :artwork="artwork"
      :navigation-artwork-ids="navigationArtworkIds"
    />
  </div>
</template>

<style scoped>
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fill,
    minmax(min(100%, var(--gallery-card-width, 220px)), 1fr)
  );
  gap: 1.5rem 0.875rem;
}
</style>
