<script setup lang="ts">
import { CheckSquare, ChevronLeft, ChevronRight, Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  bulkDeleteArtworks,
  type GalleryFilters,
  listArtworks,
  listNamed,
  listTags,
} from '@/features/gallery/gallery-api'
import {
  GALLERY_PAGE_SIZE_OPTIONS,
  loadGalleryPreferences,
  saveGalleryPreferences,
} from '@/features/gallery/gallery-preferences'
import LibraryArtworkCard from '@/features/gallery/LibraryArtworkCard.vue'
import GalleryFilterPopup from '@/pages/gallery/GalleryFilterPopup.vue'
import TopbarActions from '@/pages/gallery/TopbarActions.vue'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import FilterButton from '@ui/FilterButton.vue'
import SearchInput from '@ui/SearchInput.vue'
import Select from '@ui/Select.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'

const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()
const searchInput = ref(String(route.query.search ?? ''))
const selected = ref<number[]>([])
const deleteOpen = ref(false)
const filterOpen = ref(false)
const selectionMode = ref(false)
const authorFilterSearch = ref('')
const seriesFilterSearch = ref('')
const initialPreferences = loadGalleryPreferences()
const preferredCardWidth = ref(initialPreferences.cardWidth)
const preferredPageSize = ref(initialPreferences.pageSize)
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

function selectedTagIds() {
  const raw = route.query.tagId
  const values = Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]
  return values
    .map((value) => positiveInt(value))
    .filter((value): value is number => value !== undefined)
}

function artworkFilters(): GalleryFilters {
  const authorId = positiveInt(singleQuery('authorId'))
  const seriesId = positiveInt(singleQuery('seriesId'))
  const artworkType = singleQuery('artworkType')
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
    sort: singleQuery('sort') || 'downloadedAt',
    order: singleQuery('order') || 'desc',
  }
}

const artworksQuery = useQuery({
  queryKey: computed(() => ['artworks', artworkFilters()]),
  queryFn: () => listArtworks(artworkFilters()),
})

const tagsQuery = useQuery({ queryKey: ['tags'], queryFn: () => listTags() })
const filterAuthorsQuery = useQuery({
  queryKey: computed(() => ['filter-authors', authorFilterSearch.value]),
  queryFn: () => listNamed('authors', 0, authorFilterSearch.value),
  enabled: computed(() => filterOpen.value),
})
const filterSeriesQuery = useQuery({
  queryKey: computed(() => ['filter-series', seriesFilterSearch.value]),
  queryFn: () => listNamed('series', 0, seriesFilterSearch.value),
  enabled: computed(() => filterOpen.value),
})
const activeFilterCount = computed(() => {
  const scalarFilters = [
    singleQuery('authorId'),
    singleQuery('seriesId'),
    singleQuery('artworkType'),
    singleQuery('rating') && singleQuery('rating') !== 'all' ? singleQuery('rating') : '',
    singleQuery('ai') && singleQuery('ai') !== 'all' ? singleQuery('ai') : '',
  ]
  return selectedTagIds().length + scalarFilters.filter(Boolean).length
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

function updateSort(sort: string, order: string) {
  replaceQuery({ sort, order })
}

function updateFilter(
  name: 'authorId' | 'seriesId' | 'artworkType' | 'rating' | 'ai',
  value: string | undefined,
) {
  replaceQuery({ [name]: value })
}

function clearFilters() {
  replaceQuery({
    tagId: undefined,
    authorId: undefined,
    seriesId: undefined,
    artworkType: undefined,
    rating: undefined,
    ai: undefined,
    sort: undefined,
    order: undefined,
  })
}

function setPage(page: number) {
  replaceQuery({ page: String(page) }, false)
}

function setPageSize(value: string) {
  const parsed = Number(value)
  const selected = GALLERY_PAGE_SIZE_OPTIONS.find((size) => size === parsed)
  if (selected === undefined) return
  preferredPageSize.value = selected
  saveGalleryPreferences({
    cardWidth: preferredCardWidth.value,
    pageSize: preferredPageSize.value,
  })
  replaceQuery({})
}

function setCardWidth(value: number) {
  if (!Number.isSafeInteger(value) || value < 140 || value > 360 || value % 10 !== 0) return
  preferredCardWidth.value = value
  saveGalleryPreferences({
    cardWidth: preferredCardWidth.value,
    pageSize: preferredPageSize.value,
  })
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
                class="flex-1"
                :min="140"
                :max="360"
                :step="10"
                :model-value="preferredCardWidth"
                @update:model-value="setCardWidth"
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
        </div>
      </SettingsPopover>
    </div>
  </TopbarActions>

  <GalleryFilterPopup
    :open="filterOpen"
    :tags="tagsQuery.data.value ?? []"
    :authors="filterAuthorsQuery.data.value?.items ?? []"
    :series="filterSeriesQuery.data.value?.items ?? []"
    :selected-tag-ids="selectedTagIds()"
    :author-id="positiveInt(singleQuery('authorId'))"
    :series-id="positiveInt(singleQuery('seriesId'))"
    :artwork-type="singleQuery('artworkType')"
    :rating="singleQuery('rating') || 'all'"
    :ai="singleQuery('ai') || 'all'"
    :sort="singleQuery('sort') || 'downloadedAt'"
    :order="singleQuery('order') || 'desc'"
    :author-search="authorFilterSearch"
    :series-search="seriesFilterSearch"
    @close="filterOpen = false"
    @toggle-tag="toggleTag"
    @update-filter="updateFilter"
    @update-sort="updateSort"
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
      <p class="app-muted text-sm">{{ resultRange }}</p>
      <p v-if="singleQuery('search')" class="app-muted mt-0.5 truncate text-xs">
        搜索“{{ singleQuery('search') }}”
      </p>
    </div>

    <div v-if="artworksQuery.isPending.value" class="app-muted py-20 text-center">
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
        :selected="selected.includes(artwork.artworkId)"
        :selection-mode="selectionMode"
        @toggle-selection="toggleSelection"
        @filter-author="replaceQuery({ authorId: String($event) })"
      />
    </div>
    <Card v-else class="app-muted py-20 text-center"> 图库中没有符合条件的作品。 </Card>

    <nav class="mt-8 flex items-center justify-center gap-3">
      <Button variant="secondary" :disabled="pageNumber() === 0" @click="setPage(pageNumber() - 1)">
        <ChevronLeft :size="17" />上一页
      </Button>
      <span class="app-muted text-sm">
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
          <span class="app-muted text-sm">已选择 {{ selected.length }} 项</span>
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
