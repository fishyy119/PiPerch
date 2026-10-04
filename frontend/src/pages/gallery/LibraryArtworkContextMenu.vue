<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import type { ArtworkSummary } from '@/features/artworks/artworks-api'
import { replaceFavoriteState } from '@/features/favorites/favorites-api'
import {
  type ArtworkGroup,
  createGroup,
  listGroups,
  replaceArtworkGroups,
} from '@/features/groups/groups-api'
import {
  groupQueryKeys,
  invalidateArtworkData,
  invalidateArtworkGroupData,
} from '@/features/library/library-query-cache'
import CreateGroupDialog from '@/shared/components/groups/CreateGroupDialog.vue'
import { errorMessage } from '@/shared/errors'
import ContextMenu, { type ContextMenuOption } from '@ui/ContextMenu.vue'
import { toast } from '@ui/toast'

const props = defineProps<{ artwork: ArtworkSummary }>()
const open = defineModel<boolean>('open', { default: false })
const queryClient = useQueryClient()
const groups = ref<ArtworkGroup[]>([])
const createGroupOpen = ref(false)
const actionPending = ref(false)

const availableGroups = computed(() =>
  groups.value.filter((group) => !props.artwork.groupIds.includes(group.groupId)),
)
const currentGroups = computed(() =>
  groups.value.filter((group) => props.artwork.groupIds.includes(group.groupId)),
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
])

watch(open, (isOpen) => {
  if (!isOpen) return
  void loadGroups()
})

async function loadGroups() {
  try {
    groups.value = await queryClient.query({
      queryKey: groupQueryKeys.list(),
      queryFn: listGroups,
    })
  } catch (error) {
    toast.error('读取本地分组失败', { description: errorMessage(error) })
  }
}

async function toggleFavorite() {
  if (actionPending.value) return
  actionPending.value = true
  try {
    await replaceFavoriteState(props.artwork.artworkId, !props.artwork.isFavorite)
    await invalidateArtworkData(queryClient)
    toast.success('收藏已更新并同步到 Pixiv')
  } catch (error) {
    toast.error('更新收藏失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

async function changeGroup(groupId: number, mode: 'add' | 'remove') {
  if (actionPending.value) return
  actionPending.value = true
  try {
    const groupIds =
      mode === 'add'
        ? [...new Set([...props.artwork.groupIds, groupId])]
        : props.artwork.groupIds.filter((currentGroupId) => currentGroupId !== groupId)
    await replaceArtworkGroups(props.artwork.artworkId, groupIds)
    await invalidateArtworkGroupData(queryClient)
    toast.success(mode === 'add' ? '已添加到本地分组' : '已从本地分组移除')
  } catch (error) {
    toast.error('修改本地分组失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

async function createAndAddGroup(name: string) {
  if (actionPending.value) return
  actionPending.value = true
  try {
    const group = await createGroup(name)
    const groupIds = [...props.artwork.groupIds, group.groupId]
    await replaceArtworkGroups(props.artwork.artworkId, groupIds)
    createGroupOpen.value = false
    await invalidateArtworkGroupData(queryClient)
    toast.success('已创建本地分组并添加作品')
  } catch (error) {
    await invalidateArtworkGroupData(queryClient)
    toast.error('添加到新分组失败', { description: errorMessage(error) })
  } finally {
    actionPending.value = false
  }
}

function handleAction(action: string) {
  if (action === 'favorite') void toggleFavorite()
  else if (action === 'add-group:new') createGroupOpen.value = true
  else if (action.startsWith('add-group:')) {
    void changeGroup(Number(action.slice('add-group:'.length)), 'add')
  } else if (action.startsWith('remove-group:')) {
    void changeGroup(Number(action.slice('remove-group:'.length)), 'remove')
  }
}
</script>

<template>
  <ContextMenu v-model:open="open" :items="contextItems" @select="handleAction">
    <slot />
  </ContextMenu>

  <CreateGroupDialog
    v-if="createGroupOpen"
    :open="true"
    :description="`创建本地分组，并将“${artwork.title}”添加到该分组，不影响收藏状态。`"
    :busy="actionPending"
    @close="createGroupOpen = false"
    @save="createAndAddGroup"
  />
</template>
