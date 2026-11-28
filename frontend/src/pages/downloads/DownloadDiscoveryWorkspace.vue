<script setup lang="ts">
import { sourceOptions, useDownloadWorkspaceState } from '@/features/downloads/download-workspace'
import { Tabs } from '@ui/tabs'

import ArtworkSourceTab from './sources/ArtworkSourceTab.vue'
import BookmarkSourceTab from './sources/BookmarkSourceTab.vue'
import FanboxSourceTab from './sources/FanboxSourceTab.vue'
import FollowUpdatesSourceTab from './sources/FollowUpdatesSourceTab.vue'
import SearchSourceTab from './sources/SearchSourceTab.vue'
import SeriesSourceTab from './sources/SeriesSourceTab.vue'
import UserSourceTab from './sources/UserSourceTab.vue'

const { sourceType, setSourceType } = useDownloadWorkspaceState()
</script>

<template>
  <Tabs
    :model-value="sourceType"
    :items="sourceOptions"
    teleport-to="#topbar-actions"
    @update:model-value="setSourceType"
  >
    <template #artwork>
      <ArtworkSourceTab />
    </template>
    <template #search>
      <SearchSourceTab />
    </template>
    <template #user>
      <UserSourceTab />
    </template>
    <template #fanbox>
      <FanboxSourceTab />
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
