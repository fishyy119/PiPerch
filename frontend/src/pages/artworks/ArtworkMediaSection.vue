<script setup lang="ts">
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FolderHeart,
  Heart,
  Images,
  Plus,
  Trash2,
} from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { artworkTypeLabel } from '@/features/artworks/artwork'
import { type ArtworkDetail, deleteArtworks } from '@/features/artworks/artworks-api'
import { replaceFavoriteState } from '@/features/favorites/favorites-api'
import { createGroupAndAddArtwork } from '@/features/groups/group-actions'
import { listGroups, replaceArtworkGroups } from '@/features/groups/groups-api'
import {
  groupQueryKeys,
  invalidateArtworkData,
  invalidateArtworkGroupData,
  removeArtworkData,
  updateArtworkDetail,
} from '@/features/library/library-query-cache'
import CreateGroupDialog from '@/shared/components/groups/CreateGroupDialog.vue'
import { errorMessage } from '@/shared/errors'
import { usePageKeyboardShortcuts } from '@/shared/lib/usePageKeyboardShortcuts'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import Checkbox from '@ui/Checkbox.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import LightboxGallery, { type LightboxItem } from '@ui/LightboxGallery.vue'
import Popover from '@ui/Popover.vue'

const PAGE_SELECTOR_ITEM_SIZE_PX = 80
const PAGE_SELECTOR_GAP_PX = 8

const props = defineProps<{ artwork: ArtworkDetail }>()

const router = useRouter()
const queryClient = useQueryClient()
const selectedPage = ref<number | null>(null)
const pageSelectorExpanded = ref(false)
const pageSelectorGrid = ref<HTMLElement | null>(null)
const pageSelectorColumns = ref(Number.POSITIVE_INFINITY)
const deleteOpen = ref(false)
const groupsOpen = ref(false)
const createGroupOpen = ref(false)

const groupsQuery = useQuery({
  queryKey: groupQueryKeys.list(),
  queryFn: listGroups,
})

const deleteMutation = useMutation({
  mutationFn: () => deleteArtworks({ mode: 'single', artworkId: props.artwork.artworkId }),
  onSuccess: async () => {
    const artworkId = props.artwork.artworkId
    deleteOpen.value = false
    await router.replace('/gallery')
    await nextTick()
    removeArtworkData(queryClient, artworkId)
    await invalidateArtworkGroupData(queryClient)
  },
  onError: (error) => {
    toast.error('永久删除作品失败', { description: errorMessage(error) })
  },
})

const favoriteMutation = useMutation({
  mutationFn: (request: { artworkId: number; isFavorite: boolean }) =>
    replaceFavoriteState(request.artworkId, request.isFavorite),
  onSuccess: async (favoriteState) => {
    updateArtworkDetail(queryClient, favoriteState.artworkId, (artwork) => ({
      ...artwork,
      isFavorite: favoriteState.isFavorite,
    }))
    await invalidateArtworkData(queryClient)
    toast.success(favoriteState.isFavorite ? '已收藏' : '已取消收藏')
  },
  onError: (error) => {
    toast.error('更新收藏失败', { description: errorMessage(error) })
  },
})

const groupMutation = useMutation({
  mutationFn: (request: { artworkId: number; groupIds: number[]; selected: boolean }) =>
    replaceArtworkGroups(request.artworkId, request.groupIds),
  onSuccess: async (membership, request) => {
    updateArtworkDetail(queryClient, membership.artworkId, (artwork) => ({
      ...artwork,
      groupIds: membership.groupIds,
    }))
    await invalidateArtworkGroupData(queryClient)
    toast.success(request.selected ? '已添加到本地分组' : '已从本地分组移除')
  },
  onError: (error) => {
    toast.error('修改本地分组失败', { description: errorMessage(error) })
  },
})

const createAndAddGroupMutation = useMutation({
  mutationFn: createGroupAndAddArtwork,
  onSuccess: async (membership) => {
    createGroupOpen.value = false
    updateArtworkDetail(queryClient, membership.artworkId, (artwork) => ({
      ...artwork,
      groupIds: membership.groupIds,
    }))
    await invalidateArtworkGroupData(queryClient)
    toast.success('已创建本地分组并添加作品')
  },
  onError: async (error) => {
    await invalidateArtworkGroupData(queryClient)
    toast.error('添加到新分组失败', { description: errorMessage(error) })
  },
})

const pageIndexes = computed(() =>
  props.artwork.media
    .map((media) => media.pageIndex)
    .filter((page): page is number => page !== null)
    .sort((left, right) => left - right),
)
const currentPage = computed(() => selectedPage.value ?? pageIndexes.value[0] ?? null)
const previewUrl = computed(() => {
  if (props.artwork.artworkType === 'ugoira') {
    return `/api/artworks/${String(props.artwork.artworkId)}/cover`
  }
  return currentPage.value === null ? '' : mediaUrl(currentPage.value)
})
const lightboxItems = computed<LightboxItem[]>(() => {
  if (props.artwork.artworkType === 'ugoira') {
    return [{ src: previewUrl.value, alt: props.artwork.title }]
  }
  return pageIndexes.value.map((page, index) => ({
    src: mediaUrl(page),
    alt:
      pageIndexes.value.length > 1
        ? `${props.artwork.title} 第 ${String(index + 1)} 页`
        : props.artwork.title,
  }))
})
const lightboxInitialIndex = computed(() => {
  if (props.artwork.artworkType === 'ugoira' || currentPage.value === null) return 0
  return Math.max(pageIndexes.value.indexOf(currentPage.value), 0)
})
const visiblePageIndexes = computed(() =>
  pageSelectorExpanded.value
    ? pageIndexes.value
    : pageIndexes.value.slice(0, pageSelectorColumns.value),
)
const pageSelectorCanExpand = computed(
  () =>
    Number.isFinite(pageSelectorColumns.value) &&
    pageIndexes.value.length > pageSelectorColumns.value,
)

watch(
  () => props.artwork.artworkId,
  () => {
    selectedPage.value = null
    pageSelectorExpanded.value = false
    groupsOpen.value = false
    createGroupOpen.value = false
  },
)

watch(
  pageSelectorGrid,
  (element, _previous, onCleanup) => {
    if (element === null) return

    const updateColumns = (width: number) => {
      if (width <= 0) return
      pageSelectorColumns.value = Math.max(
        1,
        Math.floor(
          (width + PAGE_SELECTOR_GAP_PX) / (PAGE_SELECTOR_ITEM_SIZE_PX + PAGE_SELECTOR_GAP_PX),
        ),
      )
    }
    updateColumns(element.clientWidth)

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry !== undefined) updateColumns(entry.contentRect.width)
    })
    observer.observe(element)
    onCleanup(() => observer.disconnect())
  },
  { flush: 'post' },
)

function mediaUrl(page: number) {
  return `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(page)}`
}

function mediaThumbnailUrl(page: number) {
  return `${mediaUrl(page)}/thumbnail`
}

function handleLightboxIndexChange(index: number) {
  if (props.artwork.artworkType === 'ugoira') return
  const page = pageIndexes.value[index]
  if (page !== undefined) selectedPage.value = page
}

function selectAdjacentPage(offset: -1 | 1) {
  if (props.artwork.artworkType === 'ugoira') return

  const currentIndex = pageIndexes.value.indexOf(currentPage.value ?? -1)
  const nextPage = pageIndexes.value[currentIndex + offset]
  if (nextPage !== undefined) selectedPage.value = nextPage
}

function toggleFavorite() {
  favoriteMutation.mutate({
    artworkId: props.artwork.artworkId,
    isFavorite: !props.artwork.isFavorite,
  })
}

function changeGroup(groupId: number, selected: boolean) {
  groupMutation.mutate({
    artworkId: props.artwork.artworkId,
    groupIds: selected
      ? [...new Set([...props.artwork.groupIds, groupId])]
      : props.artwork.groupIds.filter((currentGroupId) => currentGroupId !== groupId),
    selected,
  })
}

function openCreateGroup() {
  groupsOpen.value = false
  createGroupOpen.value = true
}

function createAndAddGroup(name: string) {
  createAndAddGroupMutation.mutate({
    artworkId: props.artwork.artworkId,
    name,
    groupIds: props.artwork.groupIds,
  })
}

usePageKeyboardShortcuts(
  (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    if (props.artwork.artworkType === 'ugoira' || pageIndexes.value.length <= 1) return

    event.preventDefault()
    selectAdjacentPage(event.key === 'ArrowLeft' ? -1 : 1)
  },
  { allowOverlay: (overlay) => overlay.classList.contains('artwork-lightbox') },
)
</script>

<template>
  <Card as="section" class="overflow-hidden">
    <LightboxGallery
      v-slot="{ open }"
      :items="lightboxItems"
      :active-index="lightboxInitialIndex"
      @change="handleLightboxIndexChange"
    >
      <div class="h-80 bg-muted sm:h-120">
        <button
          type="button"
          class="flex size-full items-center justify-center p-2 sm:p-4"
          @click="open(lightboxInitialIndex)"
        >
          <img
            class="block h-auto max-h-full w-auto max-w-full object-contain"
            :src="previewUrl"
            :alt="artwork.title"
            decoding="async"
          />
        </button>
      </div>
    </LightboxGallery>

    <div v-if="artwork.artworkType !== 'ugoira' && pageIndexes.length > 1" class="border-t p-3">
      <div
        ref="pageSelectorGrid"
        class="grid grid-cols-[repeat(auto-fill,5rem)] justify-between gap-2"
      >
        <button
          v-for="page in visiblePageIndexes"
          :key="page"
          type="button"
          class="relative size-20 overflow-hidden rounded-lg bg-muted ring-primary transition"
          :class="currentPage === page ? 'ring-2' : 'opacity-65 hover:opacity-100'"
          @click="selectedPage = page"
        >
          <img
            class="size-full object-cover"
            :src="mediaThumbnailUrl(page)"
            alt=""
            loading="lazy"
            decoding="async"
          />
          <span
            class="absolute right-1 bottom-1 rounded bg-overlay/65 px-1.5 text-xs text-overlay-foreground"
          >
            {{ page + 1 }}
          </span>
        </button>
      </div>
      <div v-if="pageSelectorCanExpand" class="mt-2 flex justify-center">
        <Button variant="ghost" size="small" @click="pageSelectorExpanded = !pageSelectorExpanded">
          <ChevronUp v-if="pageSelectorExpanded" :size="15" />
          <ChevronDown v-else :size="15" />
          {{ pageSelectorExpanded ? '收起' : '展开全部' }}
        </Button>
      </div>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t p-3 sm:p-4">
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        <Images :size="17" />
        <span v-if="artwork.artworkType === 'ugoira'">
          {{ artwork.ugoiraFrames.length }} 帧 · 首版暂不支持播放
        </span>
        <span v-else>
          第 {{ (currentPage ?? 0) + 1 }} / {{ artwork.pageCount }} 页 ·
          {{ artworkTypeLabel(artwork.artworkType) }}
        </span>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          :variant="artwork.isFavorite ? 'secondary' : 'primary'"
          :disabled="
            favoriteMutation.isPending.value ||
            groupMutation.isPending.value ||
            createAndAddGroupMutation.isPending.value
          "
          @click="toggleFavorite"
        >
          <Heart :size="16" :fill="artwork.isFavorite ? 'currentColor' : 'none'" />
          {{ artwork.isFavorite ? '取消收藏' : '收藏' }}
        </Button>
        <Popover v-model:open="groupsOpen" align="end" content-class="p-2">
          <template #trigger>
            <Button
              variant="secondary"
              :disabled="
                favoriteMutation.isPending.value ||
                groupMutation.isPending.value ||
                createAndAddGroupMutation.isPending.value
              "
            >
              <FolderHeart :size="16" />分组管理
            </Button>
          </template>

          <div class="max-h-72 overflow-y-auto">
            <button
              type="button"
              class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="createAndAddGroupMutation.isPending.value"
              @click="openCreateGroup"
            >
              <Plus :size="17" class="text-primary" />
              <span class="truncate text-sm">新增分组</span>
            </button>
            <div class="my-1 h-px bg-border" />
            <p v-if="groupsQuery.isPending.value" class="px-2 py-3 text-sm text-muted-foreground">
              正在读取本地分组…
            </p>
            <p v-else-if="groupsQuery.error.value" class="px-2 py-3 text-sm text-destructive">
              {{ groupsQuery.error.value.message }}
            </p>
            <template v-else-if="groupsQuery.data.value?.length">
              <button
                v-for="group in groupsQuery.data.value"
                :key="group.groupId"
                type="button"
                class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="groupMutation.isPending.value"
                @click="changeGroup(group.groupId, !artwork.groupIds.includes(group.groupId))"
              >
                <Checkbox
                  class="pointer-events-none"
                  :model-value="artwork.groupIds.includes(group.groupId)"
                  :disabled="groupMutation.isPending.value"
                />
                <span class="truncate text-sm">{{ group.name }}</span>
              </button>
            </template>
            <p v-else class="px-2 py-3 text-sm text-muted-foreground">还没有本地分组。</p>
          </div>
        </Popover>
        <Button
          as="a"
          variant="secondary"
          :href="`https://www.pixiv.net/artworks/${String(artwork.artworkId)}`"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLink :size="16" />打开 Pixiv
        </Button>
        <Button
          variant="danger"
          :disabled="artwork.isFavorite"
          :title="artwork.isFavorite ? '收藏作品不可删除，请先取消收藏' : undefined"
          @click="deleteOpen = true"
        >
          <Trash2 :size="16" />永久删除
        </Button>
      </div>
    </div>
  </Card>

  <CreateGroupDialog
    :open="createGroupOpen"
    description="创建分组后会将当前作品加入该本地分组，不影响收藏状态。"
    :busy="createAndAddGroupMutation.isPending.value"
    @close="createGroupOpen = false"
    @save="createAndAddGroup"
  />

  <ConfirmDialog
    :open="deleteOpen"
    title="永久删除作品"
    description="作品记录和本地文件将被永久删除，此操作无法撤销。"
    confirm-text="永久删除"
    :busy="deleteMutation.isPending.value"
    @close="deleteOpen = false"
    @confirm="deleteMutation.mutate()"
  />
</template>
