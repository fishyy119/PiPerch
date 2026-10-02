<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, nextTick, ref, watch } from 'vue'

import { discover } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'

const selection = useDownloadSelection()
const page = ref(0)
const updatesQuery = useQuery({
  queryKey: computed(() => ['follow-updates', page.value] as const),
  queryFn: ({ queryKey }) => discover({ sourceType: 'followUpdates', page: queryKey[1] }),
  staleTime: Number.POSITIVE_INFINITY,
  gcTime: Number.POSITIVE_INFINITY,
  refetchOnMount: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  retry: false,
})
const candidates = computed(() => updatesQuery.data.value?.items ?? [])
const nextPage = computed(() => updatesQuery.data.value?.nextPage ?? null)
const displayedEmptyMessage = computed(() => {
  if (updatesQuery.isPending.value) return '正在读取关注用户更新…'
  if (updatesQuery.error.value && updatesQuery.data.value === undefined) {
    return '关注用户更新读取失败。'
  }
  return '当前没有关注作者的新作品。'
})

watch(
  () => updatesQuery.data.value,
  (result) => {
    if (result === undefined) return
    selection.remember(result.items)
    selection.removeAll(result.items.filter((item) => item.inLibrary))
  },
  { immediate: true },
)

function loadPage(targetPage: number) {
  page.value = targetPage
}

async function refresh() {
  if (page.value !== 0) {
    page.value = 0
    await nextTick()
  }
  await updatesQuery.refetch()
}
</script>

<template>
  <DiscoverySourceLayout
    :candidates="candidates"
    :page="page"
    :next-page="nextPage"
    :pending="updatesQuery.isFetching.value"
    :empty-message="displayedEmptyMessage"
    @load-page="loadPage"
  >
    <template #source>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="font-semibold">最近关注用户更新</h2>
          <p class="mt-1 text-sm text-muted-foreground">按 Pixiv 返回顺序展示关注作者的新作品。</p>
        </div>
        <Button variant="secondary" :disabled="updatesQuery.isFetching.value" @click="refresh">
          <RefreshCw :class="updatesQuery.isFetching.value ? 'animate-spin' : ''" :size="18" />
          {{ updatesQuery.isFetching.value ? '读取中…' : '刷新' }}
        </Button>
      </div>
      <p v-if="updatesQuery.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(updatesQuery.error.value) }}
      </p>
    </template>
  </DiscoverySourceLayout>
</template>
