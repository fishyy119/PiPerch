<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { watch } from 'vue'

import { listRecommendations } from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoverArtworkCard from '@/pages/discover/DiscoverArtworkCard.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import { toast } from '@ui/toast'

const selection = useDownloadSelection()
const recommendationsQuery = useQuery({
  queryKey: ['recommendations'],
  queryFn: listRecommendations,
  staleTime: Number.POSITIVE_INFINITY,
  gcTime: Number.POSITIVE_INFINITY,
  refetchOnMount: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  retry: false,
})

watch(
  () => recommendationsQuery.data.value,
  (items) => {
    if (items === undefined) return
    selection.remember(items)
    selection.removeAll(items.filter((item) => item.inLibrary))
  },
  { immediate: true },
)

async function refreshRecommendations() {
  const result = await recommendationsQuery.refetch()
  if (result.error && recommendationsQuery.data.value !== undefined) {
    toast.error('刷新发现作品失败', { description: errorMessage(result.error) })
  }
}
</script>

<template>
  <Teleport defer to="#topbar-actions">
    <Button
      variant="secondary"
      :disabled="recommendationsQuery.isFetching.value"
      @click="refreshRecommendations"
    >
      <RefreshCw :class="recommendationsQuery.isFetching.value ? 'animate-spin' : ''" :size="17" />
      刷新
    </Button>
  </Teleport>

  <div v-if="recommendationsQuery.isPending.value" class="app-muted py-20 text-center">
    正在读取发现作品…
  </div>
  <Card
    v-else-if="recommendationsQuery.error.value && recommendationsQuery.data.value === undefined"
    class="flex flex-col items-center gap-4 py-20 text-center"
  >
    <p class="text-destructive">{{ errorMessage(recommendationsQuery.error.value) }}</p>
    <Button variant="secondary" @click="refreshRecommendations">重新加载</Button>
  </Card>
  <div v-else-if="recommendationsQuery.data.value?.length" class="discover-grid">
    <DiscoverArtworkCard
      v-for="artwork in recommendationsQuery.data.value"
      :key="artwork.artworkId"
      :artwork="artwork"
      :selected="selection.selectedIds.includes(artwork.artworkId)"
      @toggle="selection.toggle"
    />
  </div>
  <Card v-else class="app-muted py-20 text-center">当前没有可展示的发现作品。</Card>
</template>

<style scoped>
.discover-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
  gap: 1.5rem 0.875rem;
}
</style>
