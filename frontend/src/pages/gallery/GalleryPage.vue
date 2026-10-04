<script setup lang="ts">
import { CheckSquare, ChevronLeft, ChevronRight } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { usePreference } from '@/app/usePreference'
import { type ArtworkListFilters, listArtworks } from '@/features/artworks/artworks-api'
import type { GalleryFilterValues } from '@/features/gallery/gallery-filter'
import {
  defaultGalleryFilterValues,
  GALLERY_RANDOM_SEED_MODULUS,
  provideGalleryFilters,
} from '@/features/gallery/gallery-filter'
import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'
import { artworkQueryKeys } from '@/features/library/library-query-cache'
import GalleryBulkSelectionBar from '@/pages/gallery/GalleryBulkSelectionBar.vue'
import GalleryFilterPopup from '@/pages/gallery/GalleryFilterPopup.vue'
import GalleryPreferencesPopover from '@/pages/gallery/GalleryPreferencesPopover.vue'
import LibraryArtworkCard from '@/pages/gallery/LibraryArtworkCard.vue'
import TopbarActions from '@/pages/gallery/TopbarActions.vue'
import { firstQueryValue } from '@/shared/lib/route-query'
import { usePageKeyboardShortcuts } from '@/shared/lib/usePageKeyboardShortcuts'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import FilterButton from '@ui/FilterButton.vue'
import SearchInput from '@ui/SearchInput.vue'

const route = useRoute()
const router = useRouter()
const selection = useGallerySelectionStore()
const routeSearch = computed(() => firstQueryValue(route.query.search))
const searchInput = ref(routeSearch.value)
const filterOpen = ref(false)
const preferredCardWidth = usePreference('gallery.cardWidth')
const preferredPageSize = usePreference('gallery.pageSize')

function positiveInt(value: string | null | undefined) {
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}

function pageNumber() {
  const parsed = Number(firstQueryValue(route.query.page))
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0
}

function randomSeed() {
  const parsed = Number(firstQueryValue(route.query.randomSeed))
  return Number.isSafeInteger(parsed) && parsed >= 0 && parsed < GALLERY_RANDOM_SEED_MODULUS
    ? parsed
    : 0
}

function selectedTagIds() {
  const raw = route.query.tagId
  const values = Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]
  return values
    .map((value) => positiveInt(value))
    .filter((value): value is number => value !== undefined)
}

function selectedGroupIds() {
  const raw = route.query.groupId
  const values = Array.isArray(raw) ? raw : raw === undefined ? [] : [raw]
  return values
    .map((value) => positiveInt(value))
    .filter((value): value is number => value !== undefined)
}

const galleryFilterValues = computed<GalleryFilterValues>({
  get() {
    return {
      selectedTagIds: selectedTagIds(),
      authorId: positiveInt(firstQueryValue(route.query.authorId)),
      seriesId: positiveInt(firstQueryValue(route.query.seriesId)),
      artworkType: firstQueryValue(route.query.artworkType),
      rating: firstQueryValue(route.query.rating) || 'all',
      ai: firstQueryValue(route.query.ai) || 'all',
      favorite: firstQueryValue(route.query.favorite) || 'all',
      selectedGroupIds: selectedGroupIds(),
      sort: firstQueryValue(route.query.sort) || 'downloadedAt',
      order: firstQueryValue(route.query.order) || 'desc',
      randomSeed: randomSeed(),
    }
  },
  set(filters) {
    updateGalleryFilters(filters)
  },
})
provideGalleryFilters(galleryFilterValues)

function artworkFilters(): ArtworkListFilters {
  const filters = galleryFilterValues.value
  return {
    page: pageNumber(),
    size: preferredPageSize.value,
    search: routeSearch.value,
    tagIds: filters.selectedTagIds,
    ...(filters.authorId === undefined ? {} : { authorId: filters.authorId }),
    ...(filters.seriesId === undefined ? {} : { seriesId: filters.seriesId }),
    ...(filters.artworkType ? { artworkType: filters.artworkType } : {}),
    rating: filters.rating,
    ai: filters.ai,
    favorite: filters.favorite,
    groupIds: filters.selectedGroupIds,
    sort: filters.sort,
    order: filters.order,
    ...(filters.sort === 'random' ? { randomSeed: filters.randomSeed } : {}),
  }
}

const artworksQuery = useQuery({
  queryKey: computed(() => artworkQueryKeys.list(artworkFilters())),
  queryFn: () => listArtworks(artworkFilters()),
})

const activeFilterCount = computed(() => {
  const filters = galleryFilterValues.value
  const scalarFilters = [
    filters.authorId,
    filters.seriesId,
    filters.artworkType,
    filters.rating !== 'all' ? filters.rating : undefined,
    filters.ai !== 'all' ? filters.ai : undefined,
    filters.favorite !== 'all' ? filters.favorite : undefined,
  ]
  return (
    filters.selectedTagIds.length +
    filters.selectedGroupIds.length +
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
const navigationArtworkIds = computed(() =>
  (artworksQuery.data.value?.items ?? []).map((artwork) => artwork.artworkId),
)
watch(routeSearch, (search) => {
  searchInput.value = search
})
watch(
  () => route.fullPath,
  () => {
    selection.clear()
  },
)
watch(preferredPageSize, () => pushQuery({}))
onBeforeUnmount(selection.reset)

function pushQuery(changes: Record<string, string | string[] | undefined>, resetPage = true) {
  const entries = Object.entries({ ...route.query, ...changes }).filter(([key, value]) => {
    if (resetPage && key === 'page') return false
    return value !== '' && value !== undefined && (!Array.isArray(value) || value.length > 0)
  })
  void router.push({ query: Object.fromEntries(entries) })
}

function submitSearch() {
  pushQuery({ search: searchInput.value.trim() })
}

function clearSearch() {
  searchInput.value = ''
  submitSearch()
}

function updateGalleryFilters(filters: GalleryFilterValues) {
  pushQuery({
    tagId: filters.selectedTagIds.map(String),
    authorId: filters.authorId === undefined ? undefined : String(filters.authorId),
    seriesId: filters.seriesId === undefined ? undefined : String(filters.seriesId),
    artworkType: filters.artworkType || undefined,
    rating: filters.rating === 'all' ? undefined : filters.rating,
    ai: filters.ai === 'all' ? undefined : filters.ai,
    favorite: filters.favorite === 'all' ? undefined : filters.favorite,
    groupId: filters.selectedGroupIds.map(String),
    sort: filters.sort === 'downloadedAt' ? undefined : filters.sort,
    order: filters.order === 'desc' ? undefined : filters.order,
    randomSeed: filters.sort === 'random' ? String(filters.randomSeed) : undefined,
  })
}

function clearFilters() {
  updateGalleryFilters(defaultGalleryFilterValues())
}

function setPage(page: number) {
  pushQuery({ page: String(page) }, false)
  window.scrollTo({ top: 0 })
}

usePageKeyboardShortcuts((event) => {
  const previousPage = event.key === 'PageUp' || event.key === 'ArrowLeft'
  const nextPage = event.key === 'PageDown' || event.key === 'ArrowRight'
  if (!previousPage && !nextPage) return

  event.preventDefault()
  const currentPage = pageNumber()
  if (previousPage) {
    if (currentPage > 0) setPage(currentPage - 1)
    return
  }

  const totalPages = artworksQuery.data.value?.totalPages ?? 0
  if (currentPage + 1 < totalPages) setPage(currentPage + 1)
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
        :variant="selection.enabled ? 'primary' : 'secondary'"
        class="hidden shrink-0 md:inline-flex"
        @click="selection.toggleMode"
      >
        <CheckSquare :size="17" />批量管理
      </Button>
    </form>
    <div class="ml-auto shrink-0"><GalleryPreferencesPopover /></div>
  </TopbarActions>

  <GalleryFilterPopup v-model:open="filterOpen" />

  <div :class="selection.enabled ? 'pb-40 sm:pb-28' : ''">
    <div class="mb-5 grid gap-3 sm:hidden">
      <div class="flex gap-2">
        <FilterButton
          :active-count="activeFilterCount"
          @toggle="filterOpen = !filterOpen"
          @clear="clearFilters"
        />
        <Button
          :variant="selection.enabled ? 'primary' : 'secondary'"
          @click="selection.toggleMode"
        >
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
      <p v-if="routeSearch" class="mt-0.5 truncate text-xs text-muted-foreground">
        搜索“{{ routeSearch }}”
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
      :style="{ '--gallery-card-width': `${String(preferredCardWidth)}px` }"
    >
      <LibraryArtworkCard
        v-for="artwork in artworksQuery.data.value.items"
        :key="artwork.artworkId"
        :artwork="artwork"
        :navigation-artwork-ids="navigationArtworkIds"
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

  <GalleryBulkSelectionBar :visible-artwork-ids="navigationArtworkIds" />
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
