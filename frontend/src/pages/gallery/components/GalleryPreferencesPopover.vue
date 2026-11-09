<script setup lang="ts">
import { computed } from 'vue'

import { usePreference } from '@/app/usePreference'
import { Select } from '@ui/select'
import { SettingsPopover } from '@ui/settings-popover'
import { Slider } from '@ui/slider'
import { Switch } from '@ui/switch'

const cardWidth = usePreference('gallery.cardWidth')
const masonryImageWidth = usePreference('gallery.masonryImageWidth')
const layout = usePreference('gallery.layout')
const pageSize = usePreference('gallery.pageSize')
const showTitle = usePreference('gallery.showTitle')
const showAuthor = usePreference('gallery.showAuthor')
const showFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const itemWidth = computed<number>({
  get: () => (layout.value === 'masonry' ? masonryImageWidth.value : cardWidth.value),
  set: (value) => {
    if (layout.value === 'masonry') masonryImageWidth.value = value
    else cardWidth.value = value
  },
})
const pageSizeOptions = [24, 48, 96].map((size) => ({
  value: String(size),
  label: `${String(size)} 项`,
}))
const layoutOptions = [
  { value: 'grid', label: '网格' },
  { value: 'masonry', label: '瀑布流' },
]

function setLayout(value: string) {
  if (value === 'grid' || value === 'masonry') layout.value = value
}

function setPageSize(value: string) {
  const selected = pageSizeOptions.find((option) => option.value === value)
  if (selected !== undefined) pageSize.value = Number(selected.value)
}
</script>

<template>
  <SettingsPopover title="图库显示设置">
    <div class="space-y-5">
      <div class="flex items-center justify-between gap-3">
        <p class="text-sm font-medium">视图布局</p>
        <Select
          size="small"
          :options="layoutOptions"
          :model-value="layout"
          @update:model-value="setLayout"
        />
      </div>
      <div class="space-y-2">
        <p class="text-sm font-medium">{{ layout === 'masonry' ? '图片大小' : '卡片大小' }}</p>
        <div class="flex items-center gap-3">
          <Slider v-model="itemWidth" class="flex-1" :min="140" :max="360" :step="10" />
          <output class="w-11 text-right text-xs tabular-nums">{{ itemWidth }}px</output>
        </div>
      </div>
      <div class="flex items-center justify-between gap-3">
        <p class="text-sm font-medium">每页数量</p>
        <Select
          size="small"
          :options="pageSizeOptions"
          :model-value="String(pageSize)"
          @update:model-value="setPageSize"
        />
      </div>
      <template v-if="layout !== 'masonry'">
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-medium">显示标题</p>
          <Switch v-model="showTitle" />
        </div>
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-medium">显示作者</p>
          <Switch v-model="showAuthor" />
        </div>
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-medium">显示收藏标记</p>
          <Switch v-model="showFavoriteIndicator" />
        </div>
      </template>
    </div>
  </SettingsPopover>
</template>
