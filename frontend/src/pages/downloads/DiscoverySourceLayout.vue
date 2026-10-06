<script setup lang="ts">
import { Check, ChevronLeft, ChevronRight, X } from '@lucide/vue'
import { computed } from 'vue'

import { usePreference } from '@/app/usePreference'
import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoveryCandidateResults from '@/pages/downloads/DiscoveryCandidateResults.vue'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'

const props = defineProps<{
  candidates: readonly DiscoveryItem[]
  page: number
  nextPage: number | null
  pending: boolean
  emptyMessage: string
}>()

const emit = defineEmits<{
  loadPage: [page: number]
}>()

const selection = useDownloadSelection()
const cardWidth = usePreference('downloadCandidates.cardWidth')
const pageFullySelected = computed(() => {
  const selectable = props.candidates.filter((item) => !item.inLibrary)
  return (
    selectable.length > 0 &&
    selectable.every((item) => selection.selectedIds.includes(item.artworkId))
  )
})

function togglePage() {
  const selectable = props.candidates.filter((item) => !item.inLibrary)
  if (pageFullySelected.value) selection.removeAll(selectable)
  else selection.addAll(selectable)
}
</script>

<template>
  <div class="space-y-4">
    <Card class="p-5">
      <slot name="source" />
    </Card>

    <Card class="overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b p-4">
        <div>
          <h2 class="font-semibold">候选作品</h2>
          <p class="text-sm text-muted-foreground">跨页选择会保留，提交任务后自动清空。</p>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="secondary" :disabled="candidates.length === 0" @click="togglePage">
            <Check :size="17" />{{ pageFullySelected ? '取消本页' : '选择本页' }}
          </Button>
          <slot name="bulk-actions" />
          <Button
            variant="ghost"
            :disabled="selection.selectedIds.length === 0"
            @click="selection.clear"
          >
            <X :size="17" />清空
          </Button>
          <SettingsPopover variant="ghost" title="候选作品显示设置">
            <div class="space-y-2">
              <p class="text-sm font-medium">卡片大小</p>
              <div class="flex items-center gap-3">
                <Slider v-model="cardWidth" class="flex-1" :min="140" :max="360" :step="10" />
                <output class="w-11 text-right text-xs tabular-nums"> {{ cardWidth }}px </output>
              </div>
            </div>
          </SettingsPopover>
        </div>
      </div>

      <DiscoveryCandidateResults
        v-if="candidates.length"
        :candidates="candidates"
        :selected-ids="selection.selectedIds"
        :card-width="cardWidth"
        @set-selection="selection.setSelected"
        @toggle="selection.toggle"
      />
      <p v-else class="p-10 text-center text-muted-foreground">{{ emptyMessage }}</p>

      <slot name="errors" />

      <div class="flex items-center justify-between border-t p-4">
        <Button
          variant="secondary"
          :disabled="page === 0 || pending"
          @click="emit('loadPage', page - 1)"
        >
          <ChevronLeft :size="17" />上一页
        </Button>
        <span class="text-sm text-muted-foreground">第 {{ page + 1 }} 页</span>
        <Button
          variant="secondary"
          :disabled="nextPage === null || pending"
          @click="nextPage !== null && emit('loadPage', nextPage)"
        >
          下一页<ChevronRight :size="17" />
        </Button>
      </div>
    </Card>
  </div>
</template>
