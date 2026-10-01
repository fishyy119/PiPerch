<script setup lang="ts">
import { Check, Search, UsersRound } from '@lucide/vue'
import { useMutation } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import {
  type FollowedUser,
  listFollowedUsers,
  listSelectableUserArtworkIds,
} from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import FollowedUserSelector from '@/pages/downloads/FollowedUserSelector.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'
import Input from '@ui/Input.vue'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const selection = useDownloadSelection()
const sourceInput = ref('')
const followedUsers = ref<FollowedUser[]>([])
const showFollowedUsers = ref(false)
const loadedAuthorSelection = ref<{ userId: number; artworkIds: number[] } | null>(null)
const selectionNotice = ref('')

const currentUserId = computed(() => {
  const value = Number(sourceInput.value.trim())
  return Number.isSafeInteger(value) && value > 0 ? value : null
})

const { candidates, page, nextPage, emptyMessage, mutation, loadPage } = useDiscoveryPagination(
  (targetPage) => {
    if (currentUserId.value === null) throw new Error('请输入有效的正整数 ID。')
    return { sourceType: 'user', userId: currentUserId.value, page: targetPage }
  },
)

const allAuthorWorksSelected = computed(() => {
  const loaded = loadedAuthorSelection.value
  return (
    loaded !== null &&
    loaded.userId === currentUserId.value &&
    loaded.artworkIds.length > 0 &&
    loaded.artworkIds.every((artworkId) => selection.selectedIds.includes(artworkId))
  )
})

const followedUsersMutation = useMutation({
  mutationFn: listFollowedUsers,
  onSuccess: (items) => {
    followedUsers.value = items
    showFollowedUsers.value = true
  },
})

const selectAllMutation = useMutation({
  mutationFn: async (userId: number) => ({
    userId,
    artworkIds: await listSelectableUserArtworkIds(userId),
  }),
  onSuccess: (result) => {
    loadedAuthorSelection.value = result
    selection.addIds(result.artworkIds)
    selectionNotice.value = result.artworkIds.length
      ? `已选择该作者的全部 ${String(result.artworkIds.length)} 个作品。`
      : '该作者没有可选择的插画或漫画。'
  },
})

function fetchFollowedUsers() {
  showFollowedUsers.value = false
  followedUsersMutation.mutate()
}

function selectFollowedUser(user: FollowedUser) {
  sourceInput.value = String(user.userId)
}

function preview() {
  showFollowedUsers.value = false
  selectionNotice.value = ''
  loadPage(0)
}

function toggleAllWorks() {
  const userId = currentUserId.value
  if (userId === null) return
  const loaded = loadedAuthorSelection.value
  if (loaded?.userId === userId) {
    if (allAuthorWorksSelected.value) selection.removeIds(loaded.artworkIds)
    else selection.addIds(loaded.artworkIds)
    return
  }
  selectAllMutation.mutate(userId)
}
</script>

<template>
  <DiscoverySourceLayout
    :candidates="candidates"
    :page="page"
    :next-page="nextPage"
    :pending="mutation.isPending.value"
    :empty-message="emptyMessage"
    @load-page="loadPage"
  >
    <template #source>
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="preview">
        <Input v-model="sourceInput" class="flex-1" placeholder="用户 ID" />
        <Button
          type="button"
          variant="secondary"
          :disabled="followedUsersMutation.isPending.value"
          @click="fetchFollowedUsers"
        >
          <UsersRound :size="18" />
          {{ followedUsersMutation.isPending.value ? '获取中…' : '获取已关注作者' }}
        </Button>
        <Button type="submit" class="sm:self-start" :disabled="mutation.isPending.value">
          <Search :size="18" />
          {{ mutation.isPending.value ? '加载中…' : '预览' }}
        </Button>
      </form>
      <p v-if="mutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(mutation.error.value) }}
      </p>
      <p v-if="followedUsersMutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(followedUsersMutation.error.value) }}
      </p>
      <div v-if="showFollowedUsers" class="mt-4 border-t pt-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold">已关注作者</h2>
          <span class="app-muted text-xs">共 {{ followedUsers.length }} 位</span>
        </div>
        <FollowedUserSelector
          :users="followedUsers"
          :selected-user-id="currentUserId"
          @select="selectFollowedUser"
        />
      </div>
    </template>
    <template #bulk-actions>
      <Button
        variant="secondary"
        :disabled="currentUserId === null || selectAllMutation.isPending.value"
        @click="toggleAllWorks"
      >
        <Check :size="17" />
        <template v-if="selectAllMutation.isPending.value">读取全部…</template>
        <template v-else-if="allAuthorWorksSelected">
          取消全部（{{ loadedAuthorSelection?.artworkIds.length ?? 0 }}）
        </template>
        <template v-else>选择全部</template>
      </Button>
    </template>
    <template v-if="selectionNotice || selectAllMutation.error.value" #errors>
      <p v-if="selectionNotice" class="px-4 pb-3 text-sm text-success">
        {{ selectionNotice }}
      </p>
      <p v-if="selectAllMutation.error.value" class="px-4 pb-3 text-sm text-destructive">
        {{ errorMessage(selectAllMutation.error.value) }}
      </p>
    </template>
  </DiscoverySourceLayout>
</template>
