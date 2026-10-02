<script setup lang="ts">
import { ref, watch } from 'vue'

import ArtworkSourceTab from '@/pages/downloads/sources/ArtworkSourceTab.vue'
import BookmarkSourceTab from '@/pages/downloads/sources/BookmarkSourceTab.vue'
import FollowUpdatesSourceTab from '@/pages/downloads/sources/FollowUpdatesSourceTab.vue'
import SeriesSourceTab from '@/pages/downloads/sources/SeriesSourceTab.vue'
import UserSourceTab from '@/pages/downloads/sources/UserSourceTab.vue'
import Tabs from '@ui/Tabs.vue'

type SourceType = 'artwork' | 'user' | 'followUpdates' | 'bookmark' | 'series'

const sourceLabel = defineModel<string>('sourceLabel', { default: '作品' })
const sourceType = ref<SourceType>('artwork')
const sourceOptions = [
  { value: 'artwork', label: '作品' },
  { value: 'user', label: '用户' },
  { value: 'followUpdates', label: '更新' },
  { value: 'bookmark', label: '收藏' },
  { value: 'series', label: '系列' },
] as const

watch(sourceType, (value) => {
  sourceLabel.value = sourceOptions.find((option) => option.value === value)?.label ?? '作品'
})
</script>

<template>
  <Tabs v-model="sourceType" :items="sourceOptions" teleport-to="#topbar-actions">
    <template #artwork>
      <ArtworkSourceTab />
    </template>
    <template #user>
      <UserSourceTab />
    </template>
    <template #followUpdates>
      <FollowUpdatesSourceTab />
    </template>
    <template #bookmark>
      <BookmarkSourceTab />
    </template>
    <template #series>
      <SeriesSourceTab />
    </template>
  </Tabs>
</template>
