<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { usePreference } from '@/app/usePreference'
import { listRelatedArtworks } from '@/features/artworks/artworks-api'
import { artworkQueryKeys } from '@/features/library/library-query-cache'
import Card from '@ui/Card.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'
import SmartCropImage from '@ui/SmartCropImage.vue'

const props = defineProps<{ artworkId: number }>()

const cardWidth = usePreference('artworkDetail.relatedCardWidth')
const relatedCount = usePreference('artworkDetail.relatedCount')
const relatedQuery = useQuery({
  queryKey: computed(() => artworkQueryKeys.related(props.artworkId, relatedCount.value)),
  queryFn: () => listRelatedArtworks(props.artworkId, relatedCount.value),
})
const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(cardWidth.value)}px), ${String(cardWidth.value)}px))`,
}))
</script>

<template>
  <Card as="section" class="p-5 sm:p-6">
    <div class="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 class="font-semibold">相关作品</h2>
        <p class="mt-1 text-xs text-muted-foreground">根据本地作品的作者和共享标签推荐。</p>
      </div>
      <SettingsPopover title="相关作品显示设置">
        <div class="w-64 space-y-4">
          <div class="space-y-2">
            <p class="text-sm font-medium">卡片大小</p>
            <div class="flex items-center gap-3">
              <Slider v-model="cardWidth" class="flex-1" :min="120" :max="320" :step="10" />
              <output class="w-11 text-right text-xs tabular-nums">{{ cardWidth }}px</output>
            </div>
          </div>
          <div class="space-y-2">
            <p class="text-sm font-medium">显示数量</p>
            <div class="flex items-center gap-3">
              <Slider v-model.lazy="relatedCount" class="flex-1" :min="10" :max="50">
                <template #value="{ value }">
                  <output class="w-11 text-right text-xs tabular-nums">{{ value }}</output>
                </template>
              </Slider>
            </div>
          </div>
        </div>
      </SettingsPopover>
    </div>
    <p v-if="relatedQuery.isPending.value" class="py-8 text-sm text-muted-foreground">
      正在查找相关作品…
    </p>
    <p v-else-if="relatedQuery.error.value" class="py-8 text-sm text-destructive">
      {{ relatedQuery.error.value.message }}
    </p>
    <div
      v-else-if="relatedQuery.data.value?.length"
      class="grid justify-between gap-4"
      :style="gridStyle"
    >
      <RouterLink
        v-for="related in relatedQuery.data.value"
        :key="related.artworkId"
        class="group block min-w-0"
        :to="`/artworks/${String(related.artworkId)}`"
      >
        <div class="aspect-square w-full overflow-hidden rounded-xl bg-muted">
          <SmartCropImage
            class="size-full object-cover transition duration-300 group-hover:scale-[1.025]"
            :src="`/api/artworks/${String(related.artworkId)}/thumbnail`"
            :alt="related.title"
            loading="lazy"
          />
        </div>
      </RouterLink>
    </div>
    <p v-else class="py-8 text-sm text-muted-foreground">本地图库中暂无相关作品。</p>
  </Card>
</template>
