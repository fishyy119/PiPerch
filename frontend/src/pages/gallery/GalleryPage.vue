<script setup lang="ts">
import { CheckSquare, ChevronLeft, ChevronRight, Heart, HeartOff, Tags, Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { usePreference } from '@/app/usePreference'
import BulkFavoriteGroupsDialog from '@/features/gallery/BulkFavoriteGroupsDialog.vue'
import CreateFavoriteGroupDialog from '@/features/gallery/CreateFavoriteGroupDialog.vue'
import {
  type ArtworkSummary,
  bulkDeleteArtworks,
  bulkSetFavorite,
  bulkUpdateFavoriteGroups,
  createFavoriteGroup,
  type GalleryFilters,
  listArtworks,
  listAuthors,
  listFavoriteGroups,
  listSeries,
  listTags,
  replaceFavoriteState,
  syncFavorite,
} from '@/features/gallery/gallery-api'
import LibraryArtworkCard from '@/features/gallery/LibraryArtworkCard.vue'
import GalleryFilterPopup from '@/pages/gallery/GalleryFilterPopup.vue'
import TopbarActions from '@/pages/gallery/TopbarActions.vue'
import { errorMessage } from '@/shared/errors'
import { usePageKeyboardShortcuts } from '@/shared/lib/usePageKeyboardShortcuts'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import FilterButton from '@ui/FilterButton.vue'
import SearchInput from '@ui/SearchInput.vue'
import Select from '@ui/Select.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'
import Switch from '@ui/Switch.vue'
import { toast } from '@ui/toast'

const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()
const searchInput = ref(String(route.query.search ?? ''))
const selected = ref<number[]>([])
const deleteOpen = ref(false)
const filterOpen = ref(false)
const selectionMode = ref(false)
const syncConfirmationArtwork = ref<ArtworkSummary | null>(null)
const newFavoriteGroupArtwork = ref<ArtworkSummary | null>(null)
const bulkFavoriteGroupsOpen = ref(false)
const tagFilterSearch = ref('')
const authorFilterSearch = ref('')
const seriesFilterSearch = ref('')
const preferredCardWidth = usePreference('gallery.cardWidth')
const preferredPageSize = usePreference('gallery.pageSize')
const preferredShowTitle = usePreference('gallery.showTitle')
const preferredShowAuthor = usePreference('gallery.showAuthor')
const preferredShowFavoriteIndicator = usePreference('gallery.showFavoriteIndicator')
const RANDOM_SEED_MODULUS = 2_147_483_647
const GALLERY_PAGE_SIZE_OPTIONS = [24, 48, 96] as const
const pageSizeOptions = GALLERY_PAGE_SIZE_OPTIONS.map((size) => ({
  value: String(size),
  label: `${String(size)} 项`,
}))

function singleQuery(name: string) {
  const value = route.query[name]
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '')
}

function positiveInt(value: string | null | undefined) {
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}

function pageNumber() {
  const parsed = Number(singleQuery('page'))
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0
}

function randomSeed() {
  const parsed = Number(singleQuery('randomSeed'))
  return Number.isSafeInteger(parsed) && parsed >= 0 && parsed < RANDOM_SEED_MODULUS ? parsed : 0
}

function selectedTagIds() {
  const raw = route.query.tagId
  const values = Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]
  return values
    .map((value) => positiveInt(value))
    .filter((value): value is number => value !== undefined)
}

function selectedFavoriteGroupIds() {
  const raw = route.query.favoriteGroupId
  const values = Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]
  return values
    .map((value) => positiveInt(value))
    .filter((value): value is number => value !== undefined)
}

function selectedAuthorIds() {
  const authorId = positiveInt(singleQuery('authorId'))
  return authorId === undefined ? [] : [authorId]
}

function artworkFilters(): GalleryFilters {
  const authorId = positiveInt(singleQuery('authorId'))
  const seriesId = positiveInt(singleQuery('seriesId'))
  const artworkType = singleQuery('artworkType')
  const sort = singleQuery('sort') || 'downloadedAt'
  return {
    page: pageNumber(),
    size: preferredPageSize.value,
    search: singleQuery('search'),
    tagIds: selectedTagIds(),
    ...(authorId === undefined ? {} : { authorId }),
    ...(seriesId === undefined ? {} : { seriesId }),
    ...(artworkType ? { artworkType } : {}),
    rating: singleQuery('rating') || 'all',
    ai: singleQuery('ai') || 'all',
    favorite: singleQuery('favorite') || 'all',
    favoriteGroupIds: selectedFavoriteGroupIds(),
    sort,
    order: singleQuery('order') || 'desc',
    ...(sort === 'random' ? { randomSeed: randomSeed() } : {}),
  }
}

const artworksQuery = useQuery({
  queryKey: computed(() => ['artworks', artworkFilters()]),
  queryFn: () => listArtworks(artworkFilters()),
})

const tagsQuery = useQuery({
  queryKey: computed(() => ['tags', tagFilterSearch.value, selectedTagIds()]),
  queryFn: () => listTags(tagFilterSearch.value, selectedTagIds()),
  placeholderData: (previousData) => previousData,
})
const favoriteGroupsQuery = useQuery({
  queryKey: ['favorite-groups'],
  queryFn: listFavoriteGroups,
})
const filterAuthorsQuery = useQuery({
  queryKey: computed(() => ['filter-authors', authorFilterSearch.value, selectedAuthorIds()]),
  queryFn: () => listAuthors(authorFilterSearch.value, selectedAuthorIds()),
  enabled: computed(() => filterOpen.value),
  placeholderData: (previousData) => previousData,
})
const filterSeriesQuery = useQuery({
  queryKey: computed(() => ['filter-series', seriesFilterSearch.value]),
  queryFn: () => listSeries(0, seriesFilterSearch.value),
  enabled: computed(() => filterOpen.value),
})
const activeFilterCount = computed(() => {
  const scalarFilters = [
    singleQuery('authorId'),
    singleQuery('seriesId'),
    singleQuery('artworkType'),
    singleQuery('rating') && singleQuery('rating') !== 'all' ? singleQuery('rating') : '',
    singleQuery('ai') && singleQuery('ai') !== 'all' ? singleQuery('ai') : '',
    singleQuery('favorite') && singleQuery('favorite') !== 'all' ? singleQuery('favorite') : '',
  ]
  return (
    selectedTagIds().length +
    selectedFavoriteGroupIds().length +
    scalarFilters.filter(Boolean).length
  )
})
const resultRange = computed(() => {
  const data = artworksQuery.data.value
  if (!data || data.totalElements === 0) return '共 0 项'
  const first = data.page * data.size + 1
  const last = Math.min((data.page + 1) * data.size, data.totalElements)
  return `共 ${String(data.totalElements)} 项，第 ${String(first)}–${String(last)} 项`
})
const visibleFullySelected = computed(() => {
  const visibleIds = (artworksQuery.data.value?.items ?? []).map((artwork) => artwork.artworkId)
  return visibleIds.length > 0 && visibleIds.every((id) => selected.value.includes(id))
})
const artworkGridStyle = computed(() => ({
  '--gallery-card-width': `${String(preferredCardWidth.value)}px`,
}))
const navigationArtworkIds = computed(() =>
  (artworksQuery.data.value?.items ?? []).map((artwork) => artwork.artworkId),
)
watch(
  () => route.query.search,
  () => {
    searchInput.value = singleQuery('search')
  },
)
watch(
  () => route.fullPath,
  () => {
    selected.value = []
  },
)
watch(
  () => favoriteGroupsQuery.data.value,
  (groups) => {
    if (groups === undefined) return
    const validIds = new Set(groups.map((group) => group.groupId))
    const selectedIds = selectedFavoriteGroupIds()
    const retainedIds = selectedIds.filter((groupId) => validIds.has(groupId))
    if (retainedIds.length !== selectedIds.length) {
      replaceQuery({ favoriteGroupId: retainedIds.map(String) })
    }
  },
)

function replaceQuery(changes: Record<string, string | string[] | undefined>, resetPage = true) {
  const entries = Object.entries({ ...route.query, ...changes }).filter(([key, value]) => {
    if (resetPage && key === 'page') return false
    if (key === 'size' || key === 'cardWidth' || key === 'cardSize') return false
    return value !== '' && value !== undefined && (!Array.isArray(value) || value.length > 0)
  })
  void router.replace({ query: Object.fromEntries(entries) })
}

function submitSearch() {
  replaceQuery({ search: searchInput.value.trim() })
}

function clearSearch() {
  searchInput.value = ''
  submitSearch()
}

function toggleTag(tagId: number) {
  replaceQuery({
    tagId: selectedTagIds().includes(tagId)
      ? selectedTagIds()
          .filter((id) => id !== tagId)
          .map(String)
      : [...selectedTagIds(), tagId].map(String),
  })
}

function toggleFavoriteGroup(groupId: number) {
  replaceQuery({
    favorite: undefined,
    favoriteGroupId: selectedFavoriteGroupIds().includes(groupId)
      ? selectedFavoriteGroupIds()
          .filter((id) => id !== groupId)
          .map(String)
      : [...selectedFavoriteGroupIds(), groupId].map(String),
  })
}

function updateSort(sort: string, order: string) {
  if (sort === 'random') {
    const currentSeed = randomSeed()
    let nextSeed = currentSeed
    while (nextSeed === currentSeed) {
      nextSeed = (crypto.getRandomValues(new Uint32Array(1))[0] ?? 0) % RANDOM_SEED_MODULUS
    }
    replaceQuery({ sort, randomSeed: String(nextSeed) })
    return
  }
  replaceQuery({ sort, order, randomSeed: undefined })
}

function updateFilter(
  name: 'authorId' | 'seriesId' | 'artworkType' | 'rating' | 'ai' | 'favorite',
  value: string | undefined,
) {
  replaceQuery(
    name === 'favorite' ? { favorite: value, favoriteGroupId: undefined } : { [name]: value },
  )
}

function clearFilters() {
  replaceQuery({
    tagId: undefined,
    authorId: undefined,
    seriesId: undefined,
    artworkType: undefined,
    rating: undefined,
    ai: undefined,
    favorite: undefined,
    favoriteGroupId: undefined,
    sort: undefined,
    order: undefined,
    randomSeed: undefined,
  })
}

function setPage(page: number) {
  replaceQuery({ page: String(page) }, false)
  window.scrollTo({ top: 0 })
}

usePageKeyboardShortcuts((event) => {
  if (event.key !== 'PageUp' && event.key !== 'PageDown') return

  event.preventDefault()
  const currentPage = pageNumber()
  if (event.key === 'PageUp') {
    if (currentPage > 0) setPage(currentPage - 1)
    return
  }

  const totalPages = artworksQuery.data.value?.totalPages ?? 0
  if (currentPage + 1 < totalPages) setPage(currentPage + 1)
})

function setPageSize(value: string) {
  const parsed = Number(value)
  const selected = GALLERY_PAGE_SIZE_OPTIONS.find((size) => size === parsed)
  if (selected === undefined) return
  preferredPageSize.value = selected
  replaceQuery({})
}

function toggleSelection(id: number) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((item) => item !== id)
    : [...selected.value, id]
}

function toggleSelectionMode() {
  selectionMode.value = !selectionMode.value
  if (!selectionMode.value) selected.value = []
}

function selectVisible() {
  const visibleIds = (artworksQuery.data.value?.items ?? []).map((artwork) => artwork.artworkId)
  selected.value = visibleFullySelected.value
    ? selected.value.filter((id) => !visibleIds.includes(id))
    : [...new Set([...selected.value, ...visibleIds])]
}

const deleteMutation = useMutation({
  mutationFn: () => bulkDeleteArtworks(selected.value),
  onSuccess: async () => {
    deleteOpen.value = false
    selected.value = []
    selectionMode.value = false
    await queryClient.invalidateQueries({ queryKey: ['artworks'] })
    await queryClient.invalidateQueries({ queryKey: ['tags'] })
  },
})

async function invalidateFavoriteData() {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['artworks'] }),
    queryClient.invalidateQueries({ queryKey: ['favorite-groups'] }),
  ])
}

const favoriteMutation = useMutation({
  mutationFn: (request: { artworkId: number; isFavorite: boolean; groupIds: number[] }) =>
    replaceFavoriteState(request.artworkId, request.isFavorite, request.groupIds),
  onSuccess: async () => {
    await invalidateFavoriteData()
    toast.success('本地收藏已更新')
  },
  onError: (error) => {
    toast.error('更新本地收藏失败', { description: errorMessage(error) })
  },
})

const singleGroupMutation = useMutation({
  mutationFn: (request: { artwork: ArtworkSummary; groupId: number; mode: 'add' | 'remove' }) =>
    bulkUpdateFavoriteGroups(
      [request.artwork.artworkId],
      request.mode === 'add' ? [request.groupId] : [],
      request.mode === 'remove' ? [request.groupId] : [],
    ),
  onSuccess: async (_result, request) => {
    await invalidateFavoriteData()
    toast.success(request.mode === 'add' ? '已添加到收藏分组' : '已从收藏分组移除')
  },
  onError: (error) => {
    toast.error('修改收藏分组失败', { description: errorMessage(error) })
  },
})

const createAndAddGroupMutation = useMutation({
  mutationFn: async (request: { artwork: ArtworkSummary; name: string }) => {
    const group = await createFavoriteGroup(request.name)
    await bulkUpdateFavoriteGroups([request.artwork.artworkId], [group.groupId], [])
    return group
  },
  onSuccess: async () => {
    newFavoriteGroupArtwork.value = null
    await invalidateFavoriteData()
    toast.success('已创建收藏分组并添加作品')
  },
  onError: async (error) => {
    await invalidateFavoriteData()
    toast.error('添加到新分组失败', { description: errorMessage(error) })
  },
})

const bulkFavoriteMutation = useMutation({
  mutationFn: (isFavorite: boolean) => bulkSetFavorite(selected.value, isFavorite),
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
    bulkUpdateFavoriteGroups(selected.value, change.addGroupIds, change.removeGroupIds),
  onSuccess: async () => {
    bulkFavoriteGroupsOpen.value = false
    await invalidateFavoriteData()
    toast.success('收藏分组已批量更新')
  },
  onError: (error) => {
    toast.error('批量修改收藏分组失败', { description: errorMessage(error) })
  },
})

const syncMutation = useMutation({
  mutationFn: (artwork: ArtworkSummary) => syncFavorite(artwork.artworkId),
  onSuccess: (result) => {
    syncConfirmationArtwork.value = null
    if (result.isFavorite) {
      toast.success('已同步到 Pixiv 公开收藏', {
        description: `远端标签：${result.tags.join('、') || '无'}`,
      })
    } else {
      toast.success('已解除 Pixiv 收藏')
    }
  },
  onError: (error) => {
    toast.error('同步到 Pixiv 失败', { description: errorMessage(error) })
  },
})

function toggleFavorite(artwork: ArtworkSummary) {
  favoriteMutation.mutate({
    artworkId: artwork.artworkId,
    isFavorite: !artwork.isFavorite,
    groupIds: artwork.isFavorite ? [] : artwork.favoriteGroupIds,
  })
}

function changeFavoriteGroup(artwork: ArtworkSummary, groupId: number, mode: 'add' | 'remove') {
  singleGroupMutation.mutate({ artwork, groupId, mode })
}

function saveNewFavoriteGroup(name: string) {
  if (newFavoriteGroupArtwork.value === null) return
  createAndAddGroupMutation.mutate({ artwork: newFavoriteGroupArtwork.value, name })
}

function requestSync(artwork: ArtworkSummary) {
  if (artwork.isFavorite) syncMutation.mutate(artwork)
  else syncConfirmationArtwork.value = artwork
}

function saveBulkGroups(addGroupIds: number[], removeGroupIds: number[]) {
  bulkGroupsMutation.mutate({ addGroupIds, removeGroupIds })
}
</script>

<template>
  <TopbarActions>
    <form
      class="hidden min-w-0 flex-1 items-center justify-start gap-2 sm:flex"
      @submit.prevent="submitSearch"
    >
      <SearchInput
        v-model="searchInput"
        class="max-w-xl min-w-40 flex-1"
        placeholder="搜索作品标题或画师…"
        clearable
        submit-button
        @clear="clearSearch"
      />

      <FilterButton
        :active-count="activeFilterCount"
        hide-label-until-large
        @toggle="filterOpen = !filterOpen"
        @clear="clearFilters"
      />

      <Button
        :variant="selectionMode ? 'primary' : 'secondary'"
        class="hidden shrink-0 md:inline-flex"
        @click="toggleSelectionMode"
      >
        <CheckSquare :size="17" />批量管理
      </Button>
    </form>
    <div class="ml-auto shrink-0">
      <SettingsPopover title="图库显示设置">
        <div class="space-y-5">
          <div class="space-y-2">
            <p class="text-sm font-medium">卡片大小</p>
            <div class="flex items-center gap-3">
              <Slider
                v-model="preferredCardWidth"
                class="flex-1"
                :min="140"
                :max="360"
                :step="10"
              />
              <output class="w-11 text-right text-xs tabular-nums">
                {{ preferredCardWidth }}px
              </output>
            </div>
          </div>
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium">每页数量</p>
            <Select
              size="small"
              :options="pageSizeOptions"
              :model-value="String(preferredPageSize)"
              @update:model-value="setPageSize"
            />
          </div>
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium">显示标题</p>
            <Switch v-model="preferredShowTitle" />
          </div>
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium">显示作者</p>
            <Switch v-model="preferredShowAuthor" />
          </div>
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium">显示收藏标记</p>
            <Switch v-model="preferredShowFavoriteIndicator" />
          </div>
        </div>
      </SettingsPopover>
    </div>
  </TopbarActions>

  <GalleryFilterPopup
    :open="filterOpen"
    :tags="tagsQuery.data.value ?? []"
    :authors="filterAuthorsQuery.data.value ?? []"
    :series="filterSeriesQuery.data.value?.items ?? []"
    :favorite-groups="favoriteGroupsQuery.data.value ?? []"
    :selected-tag-ids="selectedTagIds()"
    :author-id="positiveInt(singleQuery('authorId'))"
    :series-id="positiveInt(singleQuery('seriesId'))"
    :artwork-type="singleQuery('artworkType')"
    :rating="singleQuery('rating') || 'all'"
    :ai="singleQuery('ai') || 'all'"
    :favorite="singleQuery('favorite') || 'all'"
    :selected-favorite-group-ids="selectedFavoriteGroupIds()"
    :sort="singleQuery('sort') || 'downloadedAt'"
    :order="singleQuery('order') || 'desc'"
    :tag-search="tagFilterSearch"
    :author-search="authorFilterSearch"
    :series-search="seriesFilterSearch"
    @close="filterOpen = false"
    @toggle-tag="toggleTag"
    @toggle-favorite-group="toggleFavoriteGroup"
    @update-filter="updateFilter"
    @update-sort="updateSort"
    @update-tag-search="tagFilterSearch = $event"
    @update-author-search="authorFilterSearch = $event"
    @update-series-search="seriesFilterSearch = $event"
  />

  <div :class="selectionMode ? 'pb-40 sm:pb-28' : ''">
    <div class="mb-5 grid gap-3 sm:hidden">
      <div class="flex gap-2">
        <FilterButton
          :active-count="activeFilterCount"
          @toggle="filterOpen = !filterOpen"
          @clear="clearFilters"
        />
        <Button :variant="selectionMode ? 'primary' : 'secondary'" @click="toggleSelectionMode">
          <CheckSquare :size="17" />批量
        </Button>
      </div>

      <form class="flex w-full" @submit.prevent="submitSearch">
        <SearchInput
          v-model="searchInput"
          class="w-full"
          placeholder="搜索作品标题或画师…"
          clearable
          submit-button
          @clear="clearSearch"
        />
      </form>
    </div>

    <div class="mb-4 min-w-0">
      <p class="text-sm text-muted-foreground">{{ resultRange }}</p>
      <p v-if="singleQuery('search')" class="mt-0.5 truncate text-xs text-muted-foreground">
        搜索“{{ singleQuery('search') }}”
      </p>
    </div>

    <div v-if="artworksQuery.isPending.value" class="py-20 text-center text-muted-foreground">
      正在读取图库…
    </div>
    <div v-else-if="artworksQuery.error.value" class="py-20 text-center text-destructive">
      {{ artworksQuery.error.value.message }}
    </div>
    <div
      v-else-if="artworksQuery.data.value?.items.length"
      class="gallery-grid"
      :style="artworkGridStyle"
    >
      <LibraryArtworkCard
        v-for="artwork in artworksQuery.data.value.items"
        :key="artwork.artworkId"
        :artwork="artwork"
        :favorite-groups="favoriteGroupsQuery.data.value ?? []"
        :selected="selected.includes(artwork.artworkId)"
        :selection-mode="selectionMode"
        :show-title="preferredShowTitle"
        :show-author="preferredShowAuthor"
        :show-favorite-indicator="preferredShowFavoriteIndicator"
        :navigation-artwork-ids="navigationArtworkIds"
        @toggle-selection="toggleSelection"
        @filter-author="replaceQuery({ authorId: String($event) })"
        @toggle-favorite="toggleFavorite"
        @change-favorite-group="changeFavoriteGroup"
        @add-to-new-favorite-group="newFavoriteGroupArtwork = $event"
        @sync-favorite="requestSync"
      />
    </div>
    <Card v-else class="py-20 text-center text-muted-foreground"> 图库中没有符合条件的作品。 </Card>

    <nav class="mt-8 flex items-center justify-center gap-3">
      <Button variant="secondary" :disabled="pageNumber() === 0" @click="setPage(pageNumber() - 1)">
        <ChevronLeft :size="17" />上一页
      </Button>
      <span class="text-sm text-muted-foreground">
        第 {{ pageNumber() + 1 }} /
        {{ Math.max(1, artworksQuery.data.value?.totalPages ?? 1) }}
        页
      </span>
      <Button
        variant="secondary"
        :disabled="pageNumber() + 1 >= (artworksQuery.data.value?.totalPages ?? 0)"
        @click="setPage(pageNumber() + 1)"
      >
        下一页<ChevronRight :size="17" />
      </Button>
    </nav>
  </div>

  <Transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="translate-y-3 opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-100 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-3 opacity-0"
  >
    <div
      v-if="selectionMode"
      class="pointer-events-none fixed right-0 bottom-4 left-0 z-20 px-4 lg:left-60 lg:px-6"
    >
      <Card
        class="pointer-events-auto mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 p-3 shadow-xl"
      >
        <div class="flex items-center gap-2">
          <strong class="text-sm">批量管理</strong>
          <span class="text-sm text-muted-foreground">已选择 {{ selected.length }} 项</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            :disabled="!artworksQuery.data.value?.items.length"
            @click="selectVisible"
          >
            {{ visibleFullySelected ? '取消本页' : '选择本页' }}
          </Button>
          <Button variant="ghost" :disabled="selected.length === 0" @click="selected = []">
            清空
          </Button>
          <Button
            variant="secondary"
            :disabled="selected.length === 0 || bulkFavoriteMutation.isPending.value"
            @click="bulkFavoriteMutation.mutate(true)"
          >
            <Heart :size="17" />收藏
          </Button>
          <Button
            variant="secondary"
            :disabled="selected.length === 0 || bulkFavoriteMutation.isPending.value"
            @click="bulkFavoriteMutation.mutate(false)"
          >
            <HeartOff :size="17" />取消收藏
          </Button>
          <Button
            variant="secondary"
            :disabled="selected.length === 0"
            @click="bulkFavoriteGroupsOpen = true"
          >
            <Tags :size="17" />修改分组
          </Button>
          <Button variant="danger" :disabled="selected.length === 0" @click="deleteOpen = true">
            <Trash2 :size="17" />永久删除
          </Button>
        </div>
      </Card>
    </div>
  </Transition>

  <ConfirmDialog
    :open="deleteOpen"
    title="永久删除作品"
    :description="`将永久删除 ${String(selected.length)} 个作品及其本地文件。此操作无法撤销。`"
    confirm-text="永久删除"
    :busy="deleteMutation.isPending.value"
    @close="deleteOpen = false"
    @confirm="deleteMutation.mutate()"
  />

  <BulkFavoriteGroupsDialog
    :open="bulkFavoriteGroupsOpen"
    :groups="favoriteGroupsQuery.data.value ?? []"
    :selection-count="selected.length"
    :busy="bulkGroupsMutation.isPending.value"
    @close="bulkFavoriteGroupsOpen = false"
    @groups-changed="invalidateFavoriteData"
    @save="saveBulkGroups"
  />

  <CreateFavoriteGroupDialog
    :open="newFavoriteGroupArtwork !== null"
    :description="`创建收藏分组，并将“${newFavoriteGroupArtwork?.title ?? ''}”添加到该分组。`"
    :busy="createAndAddGroupMutation.isPending.value"
    @close="newFavoriteGroupArtwork = null"
    @save="saveNewFavoriteGroup"
  />

  <ConfirmDialog
    :open="syncConfirmationArtwork !== null"
    title="解除 Pixiv 收藏"
    description="本地未收藏该作品。继续同步会解除 Pixiv 上的公开收藏；若远端本就未收藏则不会产生写入。"
    confirm-text="继续同步"
    :busy="syncMutation.isPending.value"
    @close="syncConfirmationArtwork = null"
    @confirm="syncConfirmationArtwork && syncMutation.mutate(syncConfirmationArtwork)"
  />
</template>

<style scoped>
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fill,
    minmax(min(100%, var(--gallery-card-width, 220px)), 1fr)
  );
  gap: 1.5rem 0.875rem;
}
</style>
