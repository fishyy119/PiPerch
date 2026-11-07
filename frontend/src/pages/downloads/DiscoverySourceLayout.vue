<script setup lang="ts">
import { Check } from '@lucide/vue'
import { computed, ref } from 'vue'

import { usePreference } from '@/app/usePreference'
import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useLibraryMembershipStore } from '@/features/library/library-membership'
import DiscoveryCandidateResults from '@/pages/downloads/DiscoveryCandidateResults.vue'
import { Button } from '@ui/button'
import { Card } from '@ui/card'
import { Pagination } from '@ui/pagination'
import { SettingsPopover } from '@ui/settings-popover'
import { Slider } from '@ui/slider'

const props = withDefaults(
  defineProps<{
    candidates: readonly DiscoveryItem[]
    page: number
    nextPage: number | null
    totalPages?: number | null
    pending: boolean
    emptyMessage: string
  }>(),
  { totalPages: null },
)

const emit = defineEmits<{
  loadPage: [page: number]
}>()

const selection = useDownloadSelection()
const library = useLibraryMembershipStore()
const cardWidth = usePreference('downloadCandidates.cardWidth')
const pageInput = ref('1')
const selectableCandidates = computed(() =>
  props.candidates.filter(
    (item) => !library.isInLibrary(item.remoteId, item.inLibrary, item.source),
  ),
)
const pageFullySelected = computed(() => {
  const selectable = selectableCandidates.value
  return selectable.length > 0 && selectable.every((item) => selection.isSelected(item))
})

function togglePage() {
  const selectable = selectableCandidates.value
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
        <Pagination
          v-model="pageInput"
          compact
          :page="page"
          :next-page="nextPage"
          :total-pages="totalPages"
          :pending="pending"
          @load-page="emit('loadPage', $event)"
        />
        <div class="flex flex-wrap items-center justify-end gap-2">
          <Button variant="secondary" :disabled="candidates.length === 0" @click="togglePage">
            <Check :size="17" />{{ pageFullySelected ? '取消本页' : '选择本页' }}
          </Button>
          <slot name="bulk-actions" />
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
        :card-width="cardWidth"
      />
      <p v-else class="p-10 text-center text-muted-foreground">{{ emptyMessage }}</p>

      <div v-if="$slots.errors" class="border-t">
        <slot name="errors" />
      </div>

      <Pagination
        v-model="pageInput"
        class="border-t p-4"
        :page="page"
        :next-page="nextPage"
        :total-pages="totalPages"
        :pending="pending"
        @load-page="emit('loadPage', $event)"
      />
    </Card>
  </div>
</template>
