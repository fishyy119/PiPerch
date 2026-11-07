<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import { usePreference } from '@/app/usePreference'
import { listArtworkRecommendations } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadMarqueeSelection } from '@/features/downloads/useDownloadMarqueeSelection'
import DiscoveryArtworkCard from '@/shared/components/discovery/DiscoveryArtworkCard.vue'
import DownloadSelectionButton from '@/shared/components/downloads/DownloadSelectionButton.vue'
import { errorMessage } from '@/shared/errors'
import { Button } from '@ui/button'
import { Card } from '@ui/card'
import { SettingsPopover } from '@ui/settings-popover'
import { Slider } from '@ui/slider'
import { toast } from '@ui/toast'

const props = defineProps<{ remoteId: number }>()

const selection = useDownloadSelection()
const cardWidth = usePreference('artworkDetail.relatedCardWidth')
const recommendationsQuery = useQuery({
  queryKey: computed(() => ['artwork-recommendations', props.remoteId] as const),
  queryFn: ({ queryKey, signal }) => listArtworkRecommendations(queryKey[1], { signal }),
  staleTime: Number.POSITIVE_INFINITY,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  retry: false,
})

const selectionRoot = ref<HTMLElement | null>(null)
const marquee = useDownloadMarqueeSelection(selectionRoot)
const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(cardWidth.value)}px), ${String(cardWidth.value)}px))`,
}))

watch(
  () => recommendationsQuery.data.value,
  (items) => selection.cacheItems(items ?? []),
  { immediate: true },
)

async function refreshRecommendations() {
  const result = await recommendationsQuery.refetch()
  if (result.error && recommendationsQuery.data.value !== undefined) {
    toast.error('刷新 Pixiv 推荐失败', { description: errorMessage(result.error) })
  }
}
</script>

<template>
  <Card as="section" class="relative p-5 sm:p-6">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="font-semibold">Pixiv 推荐</h2>
        <p class="mt-1 text-xs text-muted-foreground">根据当前作品推荐，可选中后提交下载。</p>
      </div>
      <div class="flex items-center gap-2">
        <Button
          variant="secondary"
          :disabled="recommendationsQuery.isFetching.value"
          @click="refreshRecommendations"
        >
          <RefreshCw
            :class="recommendationsQuery.isFetching.value ? 'animate-spin' : ''"
            :size="18"
          />
          刷新
        </Button>
        <SettingsPopover title="Pixiv 推荐显示设置">
          <div class="space-y-2">
            <p class="text-sm font-medium">卡片大小</p>
            <div class="flex items-center gap-3">
              <Slider v-model="cardWidth" class="flex-1" :min="120" :max="320" :step="10" />
              <output class="w-11 text-right text-xs tabular-nums">{{ cardWidth }}px</output>
            </div>
          </div>
        </SettingsPopover>
      </div>
    </div>
    <p v-if="recommendationsQuery.isPending.value" class="py-8 text-sm text-muted-foreground">
      正在读取 Pixiv 推荐…
    </p>
    <div
      v-else-if="recommendationsQuery.error.value && recommendationsQuery.data.value === undefined"
      class="space-y-3 py-8"
    >
      <p class="text-sm text-destructive">{{ errorMessage(recommendationsQuery.error.value) }}</p>
      <Button variant="secondary" size="small" @click="refreshRecommendations">重新加载</Button>
    </div>
    <div
      v-else-if="recommendationsQuery.data.value?.length"
      ref="selectionRoot"
      class="grid justify-between gap-x-3.5 gap-y-6"
      :style="gridStyle"
      @click.capture="marquee.handleClick"
    >
      <DiscoveryArtworkCard
        v-for="artwork in recommendationsQuery.data.value"
        :key="artwork.remoteId"
        :artwork="artwork"
        :selected="selection.isSelected(artwork)"
        @toggle="selection.toggle"
      />
    </div>
    <p v-else class="py-8 text-sm text-muted-foreground">当前没有可展示的 Pixiv 推荐。</p>
  </Card>
  <DownloadSelectionButton source-label="作品推荐" />
</template>
