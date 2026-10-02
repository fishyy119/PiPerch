<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import { usePreference } from '@/app/usePreference'
import {
  followUser,
  listRecommendations,
  listRecommendedUsers,
  type RecommendedUser,
} from '@/features/discovery/discovery-api'
import DiscoveryArtworkCard from '@/features/discovery/DiscoveryArtworkCard.vue'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoverAuthorCard from '@/pages/discover/DiscoverAuthorCard.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Select from '@ui/Select.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'
import Tabs from '@ui/Tabs.vue'
import { toast } from '@ui/toast'

type DiscoveryView = 'artworks' | 'authors'

const selection = useDownloadSelection()
const queryClient = useQueryClient()
const activeView = ref<DiscoveryView>('artworks')
const cardWidth = usePreference('discovery.cardWidth')
const authorColumns = usePreference('discovery.authorColumns')
const DISCOVERY_AUTHOR_COLUMN_OPTIONS = [1, 2, 3] as const
const authorColumnOptions = DISCOVERY_AUTHOR_COLUMN_OPTIONS.map((columns) => ({
  value: String(columns),
  label: `${String(columns)} 栏`,
}))
const viewOptions = [
  { value: 'artworks', label: '作品' },
  { value: 'authors', label: '作者' },
] as const
const recommendedUsersKey = ['recommended-users'] as const
const cachedQueryOptions = {
  staleTime: Number.POSITIVE_INFINITY,
  gcTime: Number.POSITIVE_INFINITY,
  refetchOnMount: false,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  retry: false,
} as const
const artworkGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(cardWidth.value)}px), 1fr))`,
}))
const authorGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${String(authorColumns.value)}, minmax(0, 1fr))`,
}))
const recommendationsQuery = useQuery({
  queryKey: ['recommendations'],
  queryFn: listRecommendations,
  ...cachedQueryOptions,
})
const recommendedUsersQuery = useQuery({
  queryKey: recommendedUsersKey,
  queryFn: listRecommendedUsers,
  enabled: computed(() => activeView.value === 'authors'),
  ...cachedQueryOptions,
})

watch(
  [() => recommendationsQuery.data.value, () => recommendedUsersQuery.data.value],
  ([recommendations, authors]) => {
    const items = [
      ...(recommendations ?? []),
      ...(authors ?? []).flatMap((author) => author.artworks),
    ]
    selection.remember(items)
    selection.removeAll(items.filter((item) => item.inLibrary))
  },
  { immediate: true },
)

const followMutation = useMutation({
  mutationFn: followUser,
  onSuccess: (_, userId) => {
    queryClient.setQueryData<RecommendedUser[]>(recommendedUsersKey, (authors) =>
      authors?.map((author) =>
        author.userId === userId ? { ...author, isFollowed: true } : author,
      ),
    )
    toast.success(`已关注作者 ${String(userId)}`)
  },
  onError: (error) => {
    toast.error('关注作者失败', { description: errorMessage(error) })
  },
})

const isRefreshing = computed(() =>
  activeView.value === 'artworks'
    ? recommendationsQuery.isFetching.value
    : recommendedUsersQuery.isFetching.value,
)

async function refreshRecommendations() {
  const result = await recommendationsQuery.refetch()
  if (result.error && recommendationsQuery.data.value !== undefined) {
    toast.error('刷新发现作品失败', { description: errorMessage(result.error) })
  }
}

async function refreshRecommendedUsers() {
  const result = await recommendedUsersQuery.refetch()
  if (result.error && recommendedUsersQuery.data.value !== undefined) {
    toast.error('刷新发现作者失败', { description: errorMessage(result.error) })
  }
}

function refreshCurrentView() {
  if (activeView.value === 'artworks') void refreshRecommendations()
  else void refreshRecommendedUsers()
}

function setAuthorColumns(value: string) {
  const parsed = Number(value)
  const selected = DISCOVERY_AUTHOR_COLUMN_OPTIONS.find((columns) => columns === parsed)
  if (selected === undefined) return
  authorColumns.value = selected
}
</script>

<template>
  <Tabs v-model="activeView" :items="viewOptions" teleport-to="#topbar-actions">
    <template #actions>
      <div class="flex items-center gap-2">
        <Button variant="secondary" :disabled="isRefreshing" @click="refreshCurrentView">
          <RefreshCw :class="isRefreshing ? 'animate-spin' : ''" :size="17" />
          刷新
        </Button>
        <SettingsPopover title="发现页显示设置">
          <div v-if="activeView === 'artworks'" class="space-y-2">
            <p class="text-sm font-medium">卡片大小</p>
            <div class="flex items-center gap-3">
              <Slider v-model="cardWidth" class="flex-1" :min="140" :max="360" :step="10" />
              <output class="w-11 text-right text-xs tabular-nums"> {{ cardWidth }}px </output>
            </div>
          </div>
          <div v-else class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium">作者栏数</p>
            <Select
              size="small"
              :options="authorColumnOptions"
              :model-value="String(authorColumns)"
              @update:model-value="setAuthorColumns"
            />
          </div>
        </SettingsPopover>
      </div>
    </template>

    <template #artworks>
      <div
        v-if="recommendationsQuery.isPending.value"
        class="py-20 text-center text-muted-foreground"
      >
        正在读取发现作品…
      </div>
      <Card
        v-else-if="
          recommendationsQuery.error.value && recommendationsQuery.data.value === undefined
        "
        class="flex flex-col items-center gap-4 py-20 text-center"
      >
        <p class="text-destructive">{{ errorMessage(recommendationsQuery.error.value) }}</p>
        <Button variant="secondary" @click="refreshRecommendations">重新加载</Button>
      </Card>
      <div
        v-else-if="recommendationsQuery.data.value?.length"
        class="grid gap-x-3.5 gap-y-6"
        :style="artworkGridStyle"
      >
        <DiscoveryArtworkCard
          v-for="artwork in recommendationsQuery.data.value"
          :key="artwork.artworkId"
          :artwork="artwork"
          :selected="selection.selectedIds.includes(artwork.artworkId)"
          @toggle="selection.toggle"
        />
      </div>
      <Card v-else class="py-20 text-center text-muted-foreground">
        当前没有可展示的发现作品。
      </Card>
    </template>

    <template #authors>
      <div
        v-if="recommendedUsersQuery.isPending.value"
        class="py-20 text-center text-muted-foreground"
      >
        正在读取发现作者…
      </div>
      <Card
        v-else-if="
          recommendedUsersQuery.error.value && recommendedUsersQuery.data.value === undefined
        "
        class="flex flex-col items-center gap-4 py-20 text-center"
      >
        <p class="text-destructive">{{ errorMessage(recommendedUsersQuery.error.value) }}</p>
        <Button variant="secondary" @click="refreshRecommendedUsers">重新加载</Button>
      </Card>
      <div
        v-else-if="recommendedUsersQuery.data.value?.length"
        class="grid gap-4"
        :style="authorGridStyle"
      >
        <DiscoverAuthorCard
          v-for="author in recommendedUsersQuery.data.value"
          :key="author.userId"
          :author="author"
          :selected-ids="selection.selectedIds"
          :following="
            followMutation.isPending.value && followMutation.variables.value === author.userId
          "
          @toggle="selection.toggle"
          @follow="followMutation.mutate"
        />
      </div>
      <Card v-else class="py-20 text-center text-muted-foreground">
        当前没有可展示的发现作者。
      </Card>
    </template>
  </Tabs>
</template>
