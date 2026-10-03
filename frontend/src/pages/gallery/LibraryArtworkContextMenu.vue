<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import {
  type ArtworkSummary,
  bulkUpdateFavoriteGroups,
  createFavoriteGroup,
  type FavoriteGroup,
  listFavoriteGroups,
  replaceFavoriteState,
  syncFavorite,
} from '@/features/gallery/gallery-api'
import CreateFavoriteGroupDialog from '@/shared/components/favorites/CreateFavoriteGroupDialog.vue'
import { errorMessage } from '@/shared/errors'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import ContextMenu, { type ContextMenuOption } from '@ui/ContextMenu.vue'
import { toast } from '@ui/toast'

const props = defineProps<{ artwork: ArtworkSummary }>()
const open = defineModel<boolean>('open', { default: false })
const queryClient = useQueryClient()
const favoriteGroups = ref<FavoriteGroup[]>([])
const createGroupOpen = ref(false)
const syncConfirmationOpen = ref(false)
const actionPending = ref(false)

const availableGroups = computed(() =>
  favoriteGroups.value.filter((group) => !props.artwork.favoriteGroupIds.includes(group.groupId)),
)
const currentGroups = computed(() =>
  favoriteGroups.value.filter((group) => props.artwork.favoriteGroupIds.includes(group.groupId)),
)
const contextItems = computed<ContextMenuOption[]>(() => [
  {
    value: 'favorite',
    label: props.artwork.isFavorite ? '取消收藏' : '收藏',
    disabled: actionPending.value,
  },
  {
    value: 'add-group',
    label: '添加到分组',
    disabled: actionPending.value,
    children: [
      {
        value: 'add-group:new',
        label: '添加到新分组',
      },
      ...availableGroups.value.map((group, index) => ({
        value: `add-group:${String(group.groupId)}`,
        label: group.name,
        separatorBefore: index === 0,
      })),
    ],
  },
  ...(currentGroups.value.length === 0
    ? []
    : [
        {
          value: 'remove-group',
          label: '移除出分组',
          disabled: actionPending.value,
          children: currentGroups.value.map((group) => ({
            value: `remove-group:${String(group.groupId)}`,
            label: group.name,
          })),
        },
      ]),
  {
    value: 'sync',
    label: '同步到 Pixiv',
    separatorBefore: true,
    disabled: actionPending.value,
  },
])

watch(open, (isOpen) => {
  if (!isOpen) return
  void loadFavoriteGroups()
})

async function loadFavoriteGroups() {
  try {
    favoriteGroups.value = await queryClient.query({
      queryKey: ['favorite-groups'],
      queryFn: listFavoriteGroups,
    })
  } catch (error) {
    toast.error('读取收藏分组失败', { description: errorMessage(error) })
  }
}

async function invalidateFavoriteData() {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['artworks'] }),
    queryClient.invalidateQueries({ queryKey: ['favorite-groups'] }),
  ])
}

async function toggleFavorite() {
  if (actionPending.value) return
  actionPending.value = true
  try {
    await replaceFavoriteState(
      props.artwork.artworkId,
      !props.artwork.isFavorite,
      props.artwork.isFavorite ? [] : props.artwork.favoriteGroupIds,
    )
    await invalidateFavoriteData()
    toast.success('本地收藏已更新')
  } catch (error) {
    toast.error('更新本地收藏失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

async function changeFavoriteGroup(groupId: number, mode: 'add' | 'remove') {
  if (actionPending.value) return
  actionPending.value = true
  try {
    await bulkUpdateFavoriteGroups(
      [props.artwork.artworkId],
      mode === 'add' ? [groupId] : [],
      mode === 'remove' ? [groupId] : [],
    )
    await invalidateFavoriteData()
    toast.success(mode === 'add' ? '已添加到收藏分组' : '已从收藏分组移除')
  } catch (error) {
    toast.error('修改收藏分组失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

async function createAndAddFavoriteGroup(name: string) {
  if (actionPending.value) return
  actionPending.value = true
  try {
    const group = await createFavoriteGroup(name)
    await bulkUpdateFavoriteGroups([props.artwork.artworkId], [group.groupId], [])
    createGroupOpen.value = false
    await invalidateFavoriteData()
    toast.success('已创建收藏分组并添加作品')
  } catch (error) {
    await invalidateFavoriteData()
    toast.error('添加到新分组失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

function requestSync() {
  if (props.artwork.isFavorite) void runSync()
  else syncConfirmationOpen.value = true
}

async function runSync() {
  if (actionPending.value) return
  actionPending.value = true
  try {
    const result = await syncFavorite(props.artwork.artworkId)
    syncConfirmationOpen.value = false
    if (result.isFavorite) {
      toast.success('已同步到 Pixiv 公开收藏', {
        description: `远端标签：${result.tags.join('、') || '无'}`,
      })
    } else {
      toast.success('已解除 Pixiv 收藏')
    }
  } catch (error) {
    toast.error('同步到 Pixiv 失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

function handleAction(action: string) {
  if (action === 'favorite') void toggleFavorite()
  else if (action === 'sync') requestSync()
  else if (action === 'add-group:new') createGroupOpen.value = true
  else if (action.startsWith('add-group:')) {
    void changeFavoriteGroup(Number(action.slice('add-group:'.length)), 'add')
  } else if (action.startsWith('remove-group:')) {
    void changeFavoriteGroup(Number(action.slice('remove-group:'.length)), 'remove')
  }
}
</script>

<template>
  <ContextMenu v-model:open="open" :items="contextItems" @select="handleAction">
    <slot />
  </ContextMenu>

  <CreateFavoriteGroupDialog
    v-if="createGroupOpen"
    :open="true"
    :description="`创建收藏分组，并将“${artwork.title}”添加到该分组。`"
    :busy="actionPending"
    @close="createGroupOpen = false"
    @save="createAndAddFavoriteGroup"
  />

  <ConfirmDialog
    v-if="syncConfirmationOpen"
    :open="true"
    title="解除 Pixiv 收藏"
    description="本地未收藏该作品。继续同步会解除 Pixiv 上的公开收藏；若远端本就未收藏则不会产生写入。"
    confirm-text="继续同步"
    :busy="actionPending"
    @close="syncConfirmationOpen = false"
    @confirm="runSync"
  />
</template>
