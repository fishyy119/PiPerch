<script setup lang="ts">
import { sourceOptions, useDownloadWorkspaceState } from '@/features/downloads/download-workspace'
import ArtworkSourceTab from '@/pages/downloads/sources/ArtworkSourceTab.vue'
import BookmarkSourceTab from '@/pages/downloads/sources/BookmarkSourceTab.vue'
import FollowUpdatesSourceTab from '@/pages/downloads/sources/FollowUpdatesSourceTab.vue'
import SearchSourceTab from '@/pages/downloads/sources/SearchSourceTab.vue'
import SeriesSourceTab from '@/pages/downloads/sources/SeriesSourceTab.vue'
import UserSourceTab from '@/pages/downloads/sources/UserSourceTab.vue'
import { Tabs } from '@ui/tabs'

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
