<script setup lang="ts">
import { Heart, HeartOff, Tags, Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import {
  bulkDeleteArtworks,
  bulkSetFavorite,
  bulkUpdateFavoriteGroups,
  listFavoriteGroups,
} from '@/features/gallery/gallery-api'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import BulkFavoriteGroupsDialog from '@/pages/gallery/BulkFavoriteGroupsDialog.vue'
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
const bulkFavoriteGroupsOpen = ref(false)
const visibleFullySelected = computed(
  () =>
    props.visibleArtworkIds.length > 0 &&
    props.visibleArtworkIds.every((artworkId) => selection.isSelected(artworkId)),
)

const favoriteGroupsQuery = useQuery({
  queryKey: ['favorite-groups'],
  queryFn: listFavoriteGroups,
  enabled: computed(() => bulkFavoriteGroupsOpen.value),
})

async function invalidateFavoriteData() {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['artworks'] }),
    queryClient.invalidateQueries({ queryKey: ['favorite-groups'] }),
  ])
}

const bulkFavoriteMutation = useMutation({
  mutationFn: (isFavorite: boolean) => bulkSetFavorite(selection.selectedIds, isFavorite),
  onSuccess: async (_result, isFavorite) => {
    await invalidateFavoriteData()
    toast.success(isFavorite ? '已批量收藏' : '已批量取消收藏')
  },
  onError: (error) => {
    toast.error('批量修改收藏失败', { description: errorMessage(error) })
  },
})

const bulkGroupsMutation = useMutation({
  mutationFn: (change: { addGroupIds: number[]; removeGroupIds: number[] }) =>
    bulkUpdateFavoriteGroups(selection.selectedIds, change.addGroupIds, change.removeGroupIds),
  onSuccess: async () => {
    bulkFavoriteGroupsOpen.value = false
    await invalidateFavoriteData()
    toast.success('收藏分组已批量更新')
  },
  onError: (error) => {
    toast.error('批量修改收藏分组失败', { description: errorMessage(error) })
  },
})

const deleteMutation = useMutation({
  mutationFn: () => bulkDeleteArtworks(selection.selectedIds),
  onSuccess: async () => {
    deleteOpen.value = false
    selection.reset()
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['artworks'] }),
      queryClient.invalidateQueries({ queryKey: ['tags'] }),
    ])
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
            :disabled="selection.selectedCount === 0 || bulkFavoriteMutation.isPending.value"
            @click="bulkFavoriteMutation.mutate(true)"
          >
            <Heart :size="17" />收藏
          </Button>
          <Button
            variant="secondary"
            :disabled="selection.selectedCount === 0 || bulkFavoriteMutation.isPending.value"
            @click="bulkFavoriteMutation.mutate(false)"
          >
            <HeartOff :size="17" />取消收藏
          </Button>
          <Button
            variant="secondary"
            :disabled="selection.selectedCount === 0"
            @click="bulkFavoriteGroupsOpen = true"
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
    :description="`将永久删除 ${String(selection.selectedCount)} 个作品及其本地文件。此操作无法撤销。`"
    confirm-text="永久删除"
    :busy="deleteMutation.isPending.value"
    @close="deleteOpen = false"
    @confirm="deleteMutation.mutate()"
  />

  <BulkFavoriteGroupsDialog
    v-if="bulkFavoriteGroupsOpen"
    :open="true"
    :groups="favoriteGroupsQuery.data.value ?? []"
    :selection-count="selection.selectedCount"
    :busy="bulkGroupsMutation.isPending.value"
    @close="bulkFavoriteGroupsOpen = false"
    @groups-changed="invalidateFavoriteData"
    @save="saveBulkGroups"
  />
</template>
