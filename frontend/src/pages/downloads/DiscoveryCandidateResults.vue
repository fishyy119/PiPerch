<script setup lang="ts">
import { computed, ref } from 'vue'

import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import DiscoveryArtworkCard from '@/shared/components/discovery/DiscoveryArtworkCard.vue'
import { useMarqueeSelection } from '@/shared/lib/useMarqueeSelection'

const props = withDefaults(
  defineProps<{
    candidates: readonly DiscoveryItem[]
    selectedIds: readonly number[]
    cardWidth?: number
  }>(),
  { cardWidth: 220 },
)

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
  setSelection: [artworkIds: readonly number[]]
}>()

const selectionRoot = ref<HTMLElement | null>(null)
const marquee = useMarqueeSelection(selectionRoot, {
  selectedIds: () => props.selectedIds,
  setSelectedIds: (artworkIds) => emit('setSelection', artworkIds),
  canStart: (event) =>
    !event.ctrlKey || !(event.target instanceof Element) || !event.target.closest('a'),
})
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
      :key="item.artworkId"
      :artwork="item"
      :selected="selectedIds.includes(item.artworkId)"
      @toggle="emit('toggle', $event)"
    />
  </div>
</template>
