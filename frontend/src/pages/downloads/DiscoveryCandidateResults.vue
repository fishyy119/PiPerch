<script setup lang="ts">
import { computed, ref } from 'vue'

import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadMarqueeSelection } from '@/features/downloads/useDownloadMarqueeSelection'
import DiscoveryArtworkCard from '@/shared/components/discovery/DiscoveryArtworkCard.vue'

const props = withDefaults(
  defineProps<{
    candidates: readonly DiscoveryItem[]
    cardWidth?: number
  }>(),
  { cardWidth: 220 },
)

const selection = useDownloadSelection()
const selectionRoot = ref<HTMLElement | null>(null)
const marquee = useDownloadMarqueeSelection(selectionRoot)
const artworkGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(props.cardWidth)}px), 1fr))`,
}))
</script>

<template>
  <div
    ref="selectionRoot"
    class="grid gap-x-3.5 gap-y-6 p-4"
    :style="artworkGridStyle"
    @click.capture="marquee.handleClick"
  >
    <DiscoveryArtworkCard
      v-for="item in candidates"
      :key="`${item.source}:${String(item.remoteId)}`"
      :artwork="item"
      :selected="selection.isSelected(item)"
      @toggle="selection.toggle"
    />
  </div>
</template>
