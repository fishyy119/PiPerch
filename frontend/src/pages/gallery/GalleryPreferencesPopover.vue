<script setup lang="ts">
import { usePreference } from '@/app/usePreference'
import Select from '@ui/Select.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'
import Switch from '@ui/Switch.vue'

const cardWidth = usePreference('gallery.cardWidth')
const pageSize = usePreference('gallery.pageSize')
const showTitle = usePreference('gallery.showTitle')
const showAuthor = usePreference('gallery.showAuthor')
const showFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const pageSizeOptions = [24, 48, 96].map((size) => ({
  value: String(size),
  label: `${String(size)} 项`,
}))

function setPageSize(value: string) {
  const selected = pageSizeOptions.find((option) => option.value === value)
  if (selected !== undefined) pageSize.value = Number(selected.value)
}
</script>

<template>
  <SettingsPopover title="图库显示设置">
    <div class="space-y-5">
      <div class="space-y-2">
        <p class="text-sm font-medium">卡片大小</p>
        <div class="flex items-center gap-3">
          <Slider v-model="cardWidth" class="flex-1" :min="140" :max="360" :step="10" />
          <output class="w-11 text-right text-xs tabular-nums">{{ cardWidth }}px</output>
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
    </div>
  </SettingsPopover>
</template>
