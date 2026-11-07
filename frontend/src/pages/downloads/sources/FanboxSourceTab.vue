<script setup lang="ts">
import { Check, Search } from '@lucide/vue'
import { queryOptions, useMutation, useQueries } from '@tanstack/vue-query'
import { computed, ref } from 'vue'

import { getUserProfile, userProfileKey } from '@/features/authors/author-api'
import {
  listSelectableUserArtworkIds,
  searchFanboxAuthors,
} from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useDownloadWorkspaceStore } from '@/features/downloads/download-workspace'
import { useLibraryMembershipStore } from '@/features/library/library-membership'
import AuthorSelector from '@/pages/downloads/AuthorSelector.vue'
import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import { Button } from '@ui/button'
import { Input } from '@ui/input'

import { useDiscoveryPagination } from './useDiscoveryPagination'

const selection = useDownloadSelection()
const library = useLibraryMembershipStore()
const { takePreviewRequest } = useDownloadWorkspaceStore()
const authorName = ref('')
const authorIdInput = ref('')
const showAuthors = ref(false)
const notice = ref('')
const loadedSelection = ref<{ authorId: number; remoteIds: number[] } | null>(null)
const authorId = computed(() => {
  const value = Number(authorIdInput.value.trim())
  return Number.isSafeInteger(value) && value > 0 ? value : null
})
const { candidates, page, nextPage, totalPages, emptyMessage, mutation, loadPage } =
  useDiscoveryPagination((targetPage) => {
    if (authorId.value === null) throw new Error('请输入有效的正整数作者 ID。')
    return { sourceType: 'user', source: 'fanbox', userId: authorId.value, page: targetPage }
  }, '该页无可下载作品。')
const searchMutation = useMutation({
  mutationFn: async () => {
    const query = authorName.value.trim()
    if (!query) throw new Error('请输入作者名称。')
    return searchFanboxAuthors(query)
  },
  onSuccess: () => {
    showAuthors.value = true
  },
})
// FANBOX 作者与 Pixiv 共用账号 ID，在来源层补齐用于展示的头像。
const profileQueries = useQueries({
  queries: computed(() =>
    (searchMutation.data.value ?? []).map((user) =>
      queryOptions({
        queryKey: userProfileKey(user.userId),
        queryFn: ({ queryKey, signal }) => getUserProfile(queryKey[1], { signal }),
      }),
    ),
  ),
})
const authors = computed(() =>
  (searchMutation.data.value ?? []).map((user, index) => ({
    ...user,
    avatarUrl: profileQueries.value[index]?.data?.avatarUrl ?? null,
  })),
)
const selectableIds = computed(() =>
  (loadedSelection.value?.authorId === authorId.value
    ? loadedSelection.value.remoteIds
    : []
  ).filter((id) => !library.isInLibrary(id, false, 'fanbox')),
)
const allSelected = computed(
  () =>
    selectableIds.value.length > 0 &&
    selectableIds.value.every((id) => selection.isSelected({ source: 'fanbox', remoteId: id })),
)
const selectAllMutation = useMutation({
  mutationFn: async (id: number) => ({
    authorId: id,
    remoteIds: await listSelectableUserArtworkIds(id, 'fanbox'),
  }),
  onSuccess: (result) => {
    if (result.authorId !== authorId.value) return
    loadedSelection.value = result
    const ids = selection.add(
      result.remoteIds.map((remoteId) => ({
        source: 'fanbox',
        remoteId,
        authorId: result.authorId,
      })),
    )
    notice.value = ids.length
      ? `已选择该作者的全部 ${String(ids.length)} 个图片投稿。`
      : '该作者没有可选择的图片投稿。'
  },
})
function preview() {
  showAuthors.value = false
  notice.value = ''
  loadPage(0)
}
function toggleAll() {
  if (authorId.value === null) return
  if (allSelected.value)
    selection.remove(selectableIds.value.map((remoteId) => ({ source: 'fanbox', remoteId })))
  else selectAllMutation.mutate(authorId.value)
}
const request = takePreviewRequest('fanbox')
if (request?.sourceType === 'user') {
  authorIdInput.value = String(request.userId)
  loadPage(request.page)
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
      <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="searchMutation.mutate()">
        <Input v-model="authorName" class="flex-1" placeholder="FANBOX 作者名称" />
        <Button type="submit" variant="secondary" :disabled="searchMutation.isPending.value">
          <Search :size="18" />{{ searchMutation.isPending.value ? '搜索中…' : '搜索作者' }}
        </Button>
      </form>
      <p v-if="searchMutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(searchMutation.error.value) }}
      </p>
      <form class="mt-4 flex flex-col gap-3 sm:flex-row" @submit.prevent="preview">
        <Input v-model="authorIdInput" class="flex-1" placeholder="作者 ID" />
        <Button type="submit" :disabled="mutation.isPending.value">
          <Search :size="18" />{{ mutation.isPending.value ? '加载中…' : '预览作品' }}
        </Button>
      </form>
      <p v-if="mutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(mutation.error.value) }}
      </p>
      <div v-if="showAuthors" class="mt-4 border-t pt-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold">作者搜索结果</h2>
          <span class="text-xs text-muted-foreground"
            >共 {{ searchMutation.data.value?.length ?? 0 }} 位</span
          >
        </div>
        <AuthorSelector
          :users="authors"
          :selected-user-id="authorId"
          show-id
          empty-message="没有找到匹配的 FANBOX 作者。"
          @select="authorIdInput = String($event.userId)"
        />
      </div>
    </template>
    <template #bulk-actions>
      <Button
        variant="secondary"
        :disabled="authorId === null || selectAllMutation.isPending.value"
        @click="toggleAll"
      >
        <Check :size="17" />
        <template v-if="selectAllMutation.isPending.value">读取全部…</template>
        <template v-else-if="allSelected">取消全部（{{ selectableIds.length }}）</template>
        <template v-else>选择全部</template>
      </Button>
    </template>
    <template v-if="notice || selectAllMutation.error.value" #errors>
      <p v-if="notice" class="px-4 pb-3 text-sm text-success">{{ notice }}</p>
      <p v-if="selectAllMutation.error.value" class="px-4 pb-3 text-sm text-destructive">
        {{ errorMessage(selectAllMutation.error.value) }}
      </p>
    </template>
  </DiscoverySourceLayout>
</template>
