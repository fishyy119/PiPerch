<script setup lang="ts">
import { ImageOff, Images } from '@lucide/vue'
import { computed, ref } from 'vue'

import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import DiscoveryArtworkCard from '@/shared/components/discovery/DiscoveryArtworkCard.vue'
import Checkbox from '@ui/Checkbox.vue'

const props = withDefaults(
  defineProps<{
    candidates: readonly DiscoveryItem[]
    selectedIds: readonly number[]
    viewStyle?: 'list' | 'artwork'
    cardWidth?: number
  }>(),
  { viewStyle: 'list', cardWidth: 220 },
)

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
}>()

const failedThumbnails = ref(new Set<number>())
const artworkGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(props.cardWidth)}px), 1fr))`,
}))

function markThumbnailUnavailable(artworkId: number) {
  const next = new Set(failedThumbnails.value)
  next.add(artworkId)
  failedThumbnails.value = next
}
</script>

<template>
  <div v-if="viewStyle === 'list'" class="candidate-grid grid gap-3 p-4">
    <div
      v-for="item in candidates"
      :key="item.artworkId"
      class="relative flex min-w-0 items-center gap-3 overflow-hidden rounded-xl border p-3 transition"
      :class="[
        item.inLibrary
          ? 'cursor-not-allowed opacity-80'
          : 'cursor-pointer hover:border-primary/50 hover:shadow-sm',
        !item.inLibrary && selectedIds.includes(item.artworkId) ? 'ring-2 ring-primary' : '',
      ]"
      @click="!item.inLibrary && emit('toggle', item)"
    >
      <span
        v-if="item.inLibrary"
        class="in-library-corner absolute top-0 right-0 z-10 size-10 bg-success"
      />
      <Checkbox
        class="size-4 shrink-0"
        :model-value="!item.inLibrary && selectedIds.includes(item.artworkId)"
        :disabled="item.inLibrary"
        @click.stop
        @update:model-value="emit('toggle', item)"
      />
      <div
        class="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted"
      >
        <img
          v-if="item.thumbnailUrl && !failedThumbnails.has(item.artworkId)"
          class="size-full object-cover"
          :src="item.thumbnailUrl"
          alt=""
          loading="lazy"
          @error="markThumbnailUnavailable(item.artworkId)"
        />
        <ImageOff v-else class="text-muted-foreground" :size="22" />
      </div>
      <span class="min-w-0 flex-1">
        <strong class="block truncate text-sm" :title="item.title">{{ item.title }}</strong>
        <span class="mt-2 flex min-w-0 items-center gap-3 text-xs text-muted-foreground">
          <span class="inline-flex shrink-0 items-center gap-1">
            <Images :size="14" />{{ item.pageCount }} 张
          </span>
          <span class="truncate" :title="item.authorName">{{ item.authorName }}</span>
        </span>
      </span>
    </div>
  </div>
  <div v-else class="grid gap-x-3.5 gap-y-6 p-4" :style="artworkGridStyle">
    <DiscoveryArtworkCard
      v-for="item in candidates"
      :key="item.artworkId"
      :artwork="item"
      :selected="selectedIds.includes(item.artworkId)"
      @toggle="emit('toggle', $event)"
    />
  </div>
</template>

<style scoped>
.candidate-grid {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
}

.in-library-corner {
  clip-path: polygon(100% 0, 100% 100%, 0 0);
}
</style>
