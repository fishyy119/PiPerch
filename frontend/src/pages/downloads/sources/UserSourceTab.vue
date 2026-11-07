<script setup lang="ts">
import { Check, Search, UsersRound } from '@lucide/vue'
import { useMutation } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { type AuthorSummary, listFollowedUsers } from '@/features/authors/author-api'
import { listSelectableUserArtworkIds } from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadWorkspaceStore } from '@/features/downloads/download-workspace'
import { useLibraryMembershipStore } from '@/features/library/library-membership'
import AuthorSelector from '@/pages/downloads/AuthorSelector.vue'
import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import { Button } from '@ui/button'
import { Input } from '@ui/input'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const { takePreviewRequest } = useDownloadWorkspaceStore()
const selection = useDownloadSelection()
const library = useLibraryMembershipStore()
const sourceInput = ref('')
const followedUsers = ref<AuthorSummary[]>([])
const showFollowedUsers = ref(false)
const loadedAuthorSelection = ref<{ userId: number; remoteIds: number[] } | null>(null)
const selectionNotice = ref('')

const currentUserId = computed(() => {
  const value = Number(sourceInput.value.trim())
  return Number.isSafeInteger(value) && value > 0 ? value : null
})

const { candidates, page, nextPage, totalPages, emptyMessage, mutation, loadPage } =
  useDiscoveryPagination((targetPage) => {
    if (currentUserId.value === null) throw new Error('请输入有效的正整数 ID。')
    return { sourceType: 'user', userId: currentUserId.value, page: targetPage }
  })

const selectableAuthorArtworkIds = computed(() =>
  (loadedAuthorSelection.value?.remoteIds ?? []).filter((id) => !library.isInLibrary(id)),
)
const allAuthorWorksSelected = computed(() => {
  const loaded = loadedAuthorSelection.value
  return (
    loaded !== null &&
    loaded.userId === currentUserId.value &&
    selectableAuthorArtworkIds.value.length > 0 &&
    selectableAuthorArtworkIds.value.every((artworkId) =>
      selection.isSelected({ source: 'pixiv', remoteId: artworkId }),
    )
  )
})

const followedUsersMutation = useMutation({
  mutationFn: () => listFollowedUsers(true),
  onSuccess: (items) => {
    followedUsers.value = items
    showFollowedUsers.value = true
  },
})

const selectAllMutation = useMutation({
  mutationFn: async (userId: number) => {
    const loaded = loadedAuthorSelection.value
    const remoteIds =
      loaded?.userId === userId ? loaded.remoteIds : await listSelectableUserArtworkIds(userId)
    return { userId, remoteIds }
  },
  onSuccess: (result) => {
    loadedAuthorSelection.value = result
    const remoteIds = selection.add(
      result.remoteIds.map((remoteId) => ({ source: 'pixiv', remoteId })),
    )
    selectionNotice.value = remoteIds.length
      ? `已选择该作者的全部 ${String(remoteIds.length)} 个作品。`
      : '该作者没有可选择的插画或漫画。'
  },
})

function fetchFollowedUsers() {
  showFollowedUsers.value = false
  followedUsersMutation.mutate()
}

function selectFollowedUser(user: AuthorSummary) {
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
  if (loaded?.userId === userId && allAuthorWorksSelected.value) {
    selection.remove(
      selectableAuthorArtworkIds.value.map((remoteId) => ({ source: 'pixiv', remoteId })),
    )
    return
  }
  selectAllMutation.mutate(userId)
}

const previewRequest = takePreviewRequest('user')
if (previewRequest?.sourceType === 'user') {
  sourceInput.value = String(previewRequest.userId)
  loadPage(previewRequest.page)
}
</script>

<template>
  <DiscoverySourceLayout
    :candidates="candidates"
    :page="page"
    :next-page="nextPage"
    :total-pages="totalPages"
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
          <span class="text-xs text-muted-foreground">共 {{ followedUsers.length }} 位</span>
        </div>
        <AuthorSelector
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
          取消全部（{{ selectableAuthorArtworkIds.length }}）
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
