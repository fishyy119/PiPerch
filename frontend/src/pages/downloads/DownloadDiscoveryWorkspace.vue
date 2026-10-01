<script setup lang="ts">
import { computed, ref } from 'vue'

import ArtworkSourceTab from '@/pages/downloads/sources/ArtworkSourceTab.vue'
import BookmarkSourceTab from '@/pages/downloads/sources/BookmarkSourceTab.vue'
import SeriesSourceTab from '@/pages/downloads/sources/SeriesSourceTab.vue'
import UserSourceTab from '@/pages/downloads/sources/UserSourceTab.vue'

type SourceType = 'artwork' | 'user' | 'bookmark' | 'series'

const sourceLabel = defineModel<string>('sourceLabel', { default: '作品' })
const sourceType = ref<SourceType>('artwork')
const sourceOptions = [
  { value: 'artwork', label: '作品', component: ArtworkSourceTab },
  { value: 'user', label: '用户', component: UserSourceTab },
  { value: 'bookmark', label: '收藏', component: BookmarkSourceTab },
  { value: 'series', label: '系列', component: SeriesSourceTab },
] as const

const currentSource = computed(
  () => sourceOptions.find((option) => option.value === sourceType.value) ?? sourceOptions[0],
)

function switchSource(source: (typeof sourceOptions)[number]) {
  if (source.value === sourceType.value) return
  sourceType.value = source.value
  sourceLabel.value = source.label
}
</script>

<template>
  <component :is="currentSource.component" :key="currentSource.value">
    <template #tabs>
      <div class="mb-4 flex flex-wrap gap-2">
        <button
          v-for="option in sourceOptions"
          :key="option.value"
          type="button"
          class="cursor-pointer rounded-xl px-4 py-2 text-sm"
          :class="
            sourceType === option.value
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground'
          "
          @click="switchSource(option)"
        >
          {{ option.label }}
        </button>
      </div>
    </template>
  </component>
</template>
