<script setup lang="ts">
import { Check, RefreshCw, Search } from '@lucide/vue'
import { useMutation, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'

import {
  type BookmarkFolderReference,
  listBookmarkFolders,
  listSelectableBookmarkArtworkIds,
} from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useBookmarkPreview } from '@/features/downloads/useBookmarkPreview'
import BookmarkFolderSelector from '@/pages/downloads/BookmarkFolderSelector.vue'
import DiscoverySourceLayout from '@/pages/downloads/DiscoverySourceLayout.vue'
import { errorMessage } from '@/shared/errors'
import Button from '@ui/Button.vue'

interface LoadedBookmarkSelection {
  key: string
  artworkIds: number[]
}

const selection = useDownloadSelection()
const preview = useBookmarkPreview()
const { candidates, page, nextPage } = preview
const draftFolders = ref<BookmarkFolderReference[]>([])
const confirmedFolders = ref<BookmarkFolderReference[]>([])
const showFolders = ref(true)
const selectionNotice = ref('')
const loadedSelection = ref<LoadedBookmarkSelection | null>(null)

function folderKey(folder: BookmarkFolderReference) {
  return JSON.stringify([folder.visibility, folder.tag])
}

function selectionKey(folders: readonly BookmarkFolderReference[]) {
  return JSON.stringify(folders.map((folder) => [folder.visibility, folder.tag]))
}

function cloneFolder(folder: BookmarkFolderReference): BookmarkFolderReference {
  return { visibility: folder.visibility, tag: folder.tag }
}

const foldersQuery = useQuery({
  queryKey: ['bookmark-folders'],
  queryFn: listBookmarkFolders,
  staleTime: Number.POSITIVE_INFINITY,
  gcTime: Number.POSITIVE_INFINITY,
})
const folders = computed(() => foldersQuery.data.value ?? [])
const foldersLoaded = computed(() => foldersQuery.data.value !== undefined)

watch(
  folders,
  (items) => {
    const selectedKeys = new Set(draftFolders.value.map(folderKey))
    draftFolders.value = items
      .filter((folder) => selectedKeys.has(folderKey(folder)))
      .map(cloneFolder)
  },
  { immediate: true },
)

const confirmedFolderSummary = computed(() => {
  const keys = new Set(confirmedFolders.value.map(folderKey))
  return folders.value
    .filter((folder) => keys.has(folderKey(folder)))
    .map((folder) => `${folder.visibility === 'public' ? '公开' : '非公开'} / ${folder.name}`)
    .join('、')
})

const allWorksSelected = computed(() => {
  const loaded = loadedSelection.value
  return (
    loaded !== null &&
    loaded.key === selectionKey(confirmedFolders.value) &&
    loaded.artworkIds.length > 0 &&
    loaded.artworkIds.every((artworkId) => selection.selectedIds.includes(artworkId))
  )
})

const emptyMessage = computed(() => {
  if (confirmedFolders.value.length === 0) return '请先选择收藏夹并确认。'
  if (bookmarkPageMutation.isPending.value) return '正在加载收藏作品…'
  return '所选收藏夹中没有候选作品。'
})

const bookmarkPageMutation = useMutation({ mutationFn: preview.loadPage })

const selectAllMutation = useMutation({
  mutationFn: async (selectedFolders: BookmarkFolderReference[]) => ({
    key: selectionKey(selectedFolders),
    artworkIds: await listSelectableBookmarkArtworkIds(selectedFolders),
  }),
  onSuccess: (result) => {
    loadedSelection.value = result
    selection.addIds(result.artworkIds)
    selectionNotice.value = result.artworkIds.length
      ? `已选择收藏夹中的全部 ${String(result.artworkIds.length)} 个作品。`
      : '所选收藏夹中没有可选择的作品。'
  },
})

function refreshFolders() {
  void foldersQuery.refetch()
}

function confirmFolders() {
  if (draftFolders.value.length === 0) return
  confirmedFolders.value = draftFolders.value.map(cloneFolder)
  showFolders.value = false
  selectionNotice.value = ''
  loadedSelection.value = null
  preview.reset(confirmedFolders.value)
  bookmarkPageMutation.mutate(0)
}

function reopenFolders() {
  draftFolders.value = confirmedFolders.value.map(cloneFolder)
  showFolders.value = true
}

function cancelFolderChange() {
  draftFolders.value = confirmedFolders.value.map(cloneFolder)
  showFolders.value = false
}

function toggleAllWorks() {
  if (confirmedFolders.value.length === 0) return
  const key = selectionKey(confirmedFolders.value)
  const loaded = loadedSelection.value
  if (loaded?.key === key) {
    if (allWorksSelected.value) selection.removeIds(loaded.artworkIds)
    else selection.addIds(loaded.artworkIds)
    return
  }
  selectAllMutation.mutate(confirmedFolders.value.map(cloneFolder))
}
</script>

<template>
  <DiscoverySourceLayout
    :candidates="candidates"
    :page="page"
    :next-page="nextPage"
    :pending="bookmarkPageMutation.isPending.value"
    :empty-message="emptyMessage"
    @load-page="bookmarkPageMutation.mutate"
  >
    <template #source>
      <div v-if="showFolders">
        <p
          v-if="foldersQuery.isFetching.value && !foldersLoaded"
          class="py-6 text-center text-sm text-muted-foreground"
        >
          正在读取收藏夹…
        </p>
        <BookmarkFolderSelector
          v-else-if="foldersLoaded && folders.length"
          v-model:selected-folders="draftFolders"
          :folders="folders"
        />
        <p v-else-if="foldersLoaded" class="py-6 text-center text-sm text-muted-foreground">
          没有可用的收藏标签。
        </p>
        <div
          v-if="foldersLoaded || foldersQuery.error.value"
          class="mt-4 flex flex-wrap justify-end gap-2"
        >
          <Button v-if="confirmedFolders.length" variant="ghost" @click="cancelFolderChange">
            取消更换
          </Button>
          <Button
            variant="secondary"
            :disabled="foldersQuery.isFetching.value"
            @click="refreshFolders"
          >
            <RefreshCw :class="foldersQuery.isFetching.value ? 'animate-spin' : ''" :size="18" />
            {{ foldersQuery.isFetching.value ? '刷新中…' : '刷新' }}
          </Button>
          <Button
            :disabled="
              draftFolders.length === 0 ||
              foldersQuery.isFetching.value ||
              bookmarkPageMutation.isPending.value
            "
            @click="confirmFolders"
          >
            <Search :size="18" />确认并预览
          </Button>
        </div>
      </div>
      <div v-else-if="confirmedFolders.length" class="flex items-center gap-3">
        <p class="min-w-0 flex-1 text-sm text-muted-foreground">
          已选：<span class="text-foreground">{{ confirmedFolderSummary }}</span>
        </p>
        <Button
          variant="secondary"
          :disabled="selectAllMutation.isPending.value"
          @click="reopenFolders"
        >
          更换收藏夹
        </Button>
      </div>
      <p v-if="foldersQuery.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(foldersQuery.error.value) }}
      </p>
      <p v-if="bookmarkPageMutation.error.value" class="mt-3 text-sm text-destructive">
        {{ errorMessage(bookmarkPageMutation.error.value) }}
      </p>
    </template>
    <template #bulk-actions>
      <Button
        variant="secondary"
        :disabled="confirmedFolders.length === 0 || selectAllMutation.isPending.value"
        @click="toggleAllWorks"
      >
        <Check :size="17" />
        <template v-if="selectAllMutation.isPending.value">读取全部…</template>
        <template v-else-if="allWorksSelected">
          取消全部（{{ loadedSelection?.artworkIds.length ?? 0 }}）
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
