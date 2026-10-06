<script setup lang="ts">
import { Tags, Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { deleteArtworks } from '@/features/artworks/artworks-api'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import { bulkUpdateArtworkGroups, listGroups } from '@/features/groups/groups-api'
import {
  groupQueryKeys,
  invalidateArtworkGroupData,
  removeArtworkData,
} from '@/features/library/library-query-cache'
import BulkGroupsDialog from '@/pages/gallery/BulkGroupsDialog.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import { toast } from '@ui/toast'

const props = defineProps<{
  visibleArtworkIds: readonly number[]
}>()

const selection = useGallerySelectionStore()
const queryClient = useQueryClient()
const deleteOpen = ref(false)
const bulkGroupsOpen = ref(false)
const visibleFullySelected = computed(
  () =>
    props.visibleArtworkIds.length > 0 &&
    props.visibleArtworkIds.every((artworkId) => selection.isSelected(artworkId)),
)

const groupsQuery = useQuery({
  queryKey: groupQueryKeys.list(),
  queryFn: listGroups,
  enabled: computed(() => bulkGroupsOpen.value),
})

const bulkGroupsMutation = useMutation({
  mutationFn: (change: { addGroupIds: number[]; removeGroupIds: number[] }) =>
    bulkUpdateArtworkGroups(selection.selectedIds, change.addGroupIds, change.removeGroupIds),
  onSuccess: async () => {
    bulkGroupsOpen.value = false
    await invalidateArtworkGroupData(queryClient)
    toast.success('本地分组已批量更新')
  },
  onError: (error) => {
    toast.error('批量修改本地分组失败', { description: errorMessage(error) })
  },
})

const deleteMutation = useMutation({
  mutationFn: async () => {
    const artworkIds = selection.selectedIds
    const result = await deleteArtworks({ mode: 'bulk', artworkIds })
    return { artworkIds, result }
  },
  onSuccess: async ({ artworkIds, result }) => {
    deleteOpen.value = false
    const skippedIds = new Set(result.skippedFavoriteArtworkIds)
    artworkIds
      .filter((artworkId) => !skippedIds.has(artworkId))
      .forEach((artworkId) => removeArtworkData(queryClient, artworkId))
    if (result.skippedFavoriteArtworkIds.length > 0) {
      selection.setSelected(result.skippedFavoriteArtworkIds)
      toast.warning(`已删除 ${String(result.deleted)} 个作品`, {
        description: `已跳过 ${String(result.skippedFavoriteArtworkIds.length)} 个收藏作品。`,
      })
    } else {
      selection.reset()
      toast.success(`已删除 ${String(result.deleted)} 个作品`)
    }
    await invalidateArtworkGroupData(queryClient)
  },
  onError: (error) => {
    toast.error('批量删除作品失败', { description: errorMessage(error) })
  },
})

function saveBulkGroups(addGroupIds: number[], removeGroupIds: number[]) {
  bulkGroupsMutation.mutate({ addGroupIds, removeGroupIds })
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="translate-y-3 opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-100 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-3 opacity-0"
  >
    <div
      v-if="selection.enabled"
      class="pointer-events-none fixed right-0 bottom-4 left-0 z-20 px-4 lg:left-60 lg:px-6"
    >
      <Card
        class="pointer-events-auto mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 p-3 shadow-xl"
      >
        <div class="flex items-center gap-2">
          <strong class="text-sm">批量管理</strong>
          <span class="text-sm text-muted-foreground">
            已选择 {{ selection.selectedCount }} 项
          </span>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            :disabled="visibleArtworkIds.length === 0"
            @click="selection.toggleVisible(visibleArtworkIds)"
          >
            {{ visibleFullySelected ? '取消本页' : '选择本页' }}
          </Button>
          <Button
            variant="ghost"
            :disabled="selection.selectedCount === 0"
            @click="selection.clear"
          >
            清空
          </Button>
          <Button
            variant="secondary"
            :disabled="selection.selectedCount === 0"
            @click="bulkGroupsOpen = true"
          >
            <Tags :size="17" />修改分组
          </Button>
          <Button
            variant="danger"
            :disabled="selection.selectedCount === 0"
            @click="deleteOpen = true"
          >
            <Trash2 :size="17" />永久删除
          </Button>
        </div>
      </Card>
    </div>
  </Transition>

  <ConfirmDialog
    v-if="deleteOpen"
    :open="true"
    title="永久删除作品"
    :description="`将永久删除所选作品及其本地文件，收藏作品会被保留。当前选择 ${String(selection.selectedCount)} 项。此操作无法撤销。`"
    confirm-text="永久删除"
    :busy="deleteMutation.isPending.value"
    @close="deleteOpen = false"
    @confirm="deleteMutation.mutate()"
  />

  <BulkGroupsDialog
    v-if="bulkGroupsOpen"
    :open="true"
    :groups="groupsQuery.data.value ?? []"
    :selection-count="selection.selectedCount"
    :busy="bulkGroupsMutation.isPending.value"
    @close="bulkGroupsOpen = false"
    @groups-changed="invalidateArtworkGroupData(queryClient)"
    @save="saveBulkGroups"
  />
</template>
