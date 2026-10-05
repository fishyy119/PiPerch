<script setup lang="ts">
import { ArrowDown, ArrowUp } from '@lucide/vue'
import { computed, watch } from 'vue'

import { GALLERY_RANDOM_SEED_MODULUS, useGalleryFilters } from '@/features/gallery/gallery-filter'
import { useGalleryFilterOptions } from '@/features/gallery/useGalleryFilterOptions'
import CollapsibleFilterOptions from '@/pages/gallery/CollapsibleFilterOptions.vue'
import FilterMatchToggle from '@/pages/gallery/FilterMatchToggle.vue'
import FilterOptionButton from '@/pages/gallery/FilterOptionButton.vue'
import Button from '@ui/Button.vue'
import Dialog from '@ui/Dialog.vue'
import SearchInput from '@ui/SearchInput.vue'

const open = defineModel<boolean>('open', { required: true })
const { filters, update: updateFilters } = useGalleryFilters()

const { tagSearch, authorSearch, seriesSearch, tags, authors, series, groups, groupsReady } =
  useGalleryFilterOptions({
    open: () => open.value,
    selectedTagIds: () => filters.value.selectedTagIds,
    authorId: () => filters.value.authorId,
  })

const visibleTags = computed(() => {
  const selectedIds = new Set(filters.value.selectedTagIds)
  return activeFirst(tags.value, (tag) => selectedIds.has(tag.tagId))
})
const visibleAuthors = computed(() =>
  activeFirst(authors.value, (author) => author.itemId === filters.value.authorId),
)
const visibleSeries = computed(() =>
  activeFirst(series.value, (item) => item.itemId === filters.value.seriesId),
)
const visibleGroups = computed(() => {
  const selectedIds = new Set(filters.value.selectedGroupIds)
  return activeFirst(groups.value, (group) => selectedIds.has(group.groupId))
})

function activeFirst<T>(items: T[], isActive: (item: T) => boolean) {
  return [...items].sort((left, right) => Number(isActive(right)) - Number(isActive(left)))
}

watch([groups, groupsReady], ([availableGroups, ready]) => {
  if (!ready) return
  const validIds = new Set(availableGroups.map((group) => group.groupId))
  const selectedIds = filters.value.selectedGroupIds
  const retainedIds = selectedIds.filter((groupId) => validIds.has(groupId))
  if (retainedIds.length !== selectedIds.length) {
    updateFilters({ selectedGroupIds: retainedIds })
  }
})

function toggleTag(tagId: number) {
  const selectedTagIds = filters.value.selectedTagIds.includes(tagId)
    ? filters.value.selectedTagIds.filter((id) => id !== tagId)
    : [...filters.value.selectedTagIds, tagId]
  updateFilters({ selectedTagIds })
}

function toggleGroup(groupId: number) {
  const selectedGroupIds = filters.value.selectedGroupIds.includes(groupId)
    ? filters.value.selectedGroupIds.filter((id) => id !== groupId)
    : [...filters.value.selectedGroupIds, groupId]
  updateFilters({ selectedGroupIds })
}

function updateSort(sort: string, order: string) {
  if (sort !== 'random') {
    updateFilters({ sort, order })
    return
  }

  let randomSeed = filters.value.randomSeed
  while (randomSeed === filters.value.randomSeed) {
    randomSeed = (crypto.getRandomValues(new Uint32Array(1))[0] ?? 0) % GALLERY_RANDOM_SEED_MODULUS
  }
  updateFilters({ sort, order, randomSeed })
}
</script>

<template>
  <Dialog
    v-model:open="open"
    position="top"
    title="筛选本地作品"
    title-class="mb-5"
    content-class="p-4 sm:p-6 lg:left-60"
    overlay-class="top-16 lg:left-60"
  >
    <div class="grid gap-x-6 gap-y-5">
      <section class="filter-row">
        <div class="filter-row-title flex items-center gap-1">
          <h3>排序</h3>
          <Button
            v-if="filters.sort !== 'random'"
            variant="ghost"
            size="iconSmall"
            class="-my-1 shrink-0 rounded-full text-muted-foreground"
            @click="updateSort(filters.sort, filters.order === 'desc' ? 'asc' : 'desc')"
          >
            <ArrowDown v-if="filters.order === 'desc'" :size="15" />
            <ArrowUp v-else :size="15" />
          </Button>
        </div>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="option in [
              { value: 'downloadedAt', label: '下载时间' },
              { value: 'publishedAt', label: '发布时间' },
              { value: 'id', label: '作品 ID' },
              { value: 'title', label: '标题' },
              { value: 'random', label: '随机' },
            ]"
            :key="option.value"
            :active="filters.sort === option.value"
            @click="updateSort(option.value, filters.order)"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row">
        <h3 class="filter-row-title">类型</h3>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="option in [
              { value: '', label: '全部' },
              { value: 'illust', label: '插画' },
              { value: 'manga', label: '漫画' },
              { value: 'ugoira', label: 'Ugoira' },
            ]"
            :key="option.value"
            :active="filters.artworkType === option.value"
            @click="updateFilters({ artworkType: option.value })"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row">
        <h3 class="filter-row-title">R18</h3>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="option in [
              { value: 'all', label: '全部' },
              { value: 'safe', label: '仅全年龄' },
              { value: 'r18', label: '仅 R18' },
            ]"
            :key="option.value"
            :active="filters.rating === option.value"
            @click="updateFilters({ rating: option.value })"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row">
        <h3 class="filter-row-title">AI</h3>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="option in [
              { value: 'all', label: '全部' },
              { value: 'yes', label: '仅 AI' },
              { value: 'no', label: '排除 AI' },
            ]"
            :key="option.value"
            :active="filters.ai === option.value"
            @click="updateFilters({ ai: option.value })"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row">
        <h3 class="filter-row-title">收藏</h3>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="option in [
              { value: 'all', label: '全部' },
              { value: 'yes', label: '已收藏' },
              { value: 'no', label: '未收藏' },
            ]"
            :key="option.value"
            :active="filters.favorite === option.value"
            @click="updateFilters({ favorite: option.value })"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <div class="filter-row-title flex flex-col items-start gap-1.5">
          <h3>本地分组</h3>
          <FilterMatchToggle
            :model-value="filters.groupMatch"
            @update:model-value="updateFilters({ groupMatch: $event })"
          />
        </div>
        <div class="flex flex-wrap gap-2">
          <FilterOptionButton
            v-for="group in visibleGroups"
            :key="group.groupId"
            :active="filters.selectedGroupIds.includes(group.groupId)"
            @click="toggleGroup(group.groupId)"
          >
            {{ group.name }}
            <span class="text-xs text-muted-foreground">{{ group.artworkCount }}</span>
          </FilterOptionButton>
          <span v-if="visibleGroups.length === 0" class="text-sm text-muted-foreground">
            还没有本地分组。
          </span>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <div class="filter-row-title flex flex-col items-start gap-1.5">
          <h3>标签</h3>
          <FilterMatchToggle
            :model-value="filters.tagMatch"
            @update:model-value="updateFilters({ tagMatch: $event })"
          />
        </div>
        <div>
          <SearchInput v-model="tagSearch" class="mb-3 w-full max-w-sm" placeholder="搜索标签…" />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-for="tag in visibleTags"
              :key="tag.tagId"
              :active="filters.selectedTagIds.includes(tag.tagId)"
              @click="toggleTag(tag.tagId)"
            >
              {{ tag.name }}
              <span class="text-xs text-muted-foreground">{{ tag.artworkCount ?? 0 }}</span>
            </FilterOptionButton>
            <span v-if="visibleTags.length === 0" class="text-sm text-muted-foreground">
              没有匹配的本地标签。
            </span>
          </CollapsibleFilterOptions>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <h3 class="filter-row-title">作者</h3>
        <div>
          <SearchInput
            v-model="authorSearch"
            class="mb-3 w-full max-w-sm"
            placeholder="搜索作者…"
          />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-if="
                filters.authorId && !visibleAuthors.some((item) => item.itemId === filters.authorId)
              "
              :active="true"
              @click="updateFilters({ authorId: undefined })"
            >
              作者 #{{ filters.authorId }}
            </FilterOptionButton>
            <FilterOptionButton
              v-for="author in visibleAuthors"
              :key="author.itemId"
              :active="filters.authorId === author.itemId"
              @click="
                updateFilters({
                  authorId: filters.authorId === author.itemId ? undefined : author.itemId,
                })
              "
            >
              {{ author.name }}
              <span class="text-xs text-muted-foreground">{{ author.count }}</span>
            </FilterOptionButton>
            <span v-if="visibleAuthors.length === 0" class="text-sm text-muted-foreground">
              没有匹配的本地作者。
            </span>
          </CollapsibleFilterOptions>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <h3 class="filter-row-title">系列</h3>
        <div>
          <SearchInput
            v-model="seriesSearch"
            class="mb-3 w-full max-w-sm"
            placeholder="搜索系列…"
          />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-if="
                filters.seriesId && !visibleSeries.some((item) => item.itemId === filters.seriesId)
              "
              :active="true"
              @click="updateFilters({ seriesId: undefined })"
            >
              系列 #{{ filters.seriesId }}
            </FilterOptionButton>
            <FilterOptionButton
              v-for="item in visibleSeries"
              :key="item.itemId"
              :active="filters.seriesId === item.itemId"
              @click="
                updateFilters({
                  seriesId: filters.seriesId === item.itemId ? undefined : item.itemId,
                })
              "
            >
              {{ item.name }} <span class="text-xs text-muted-foreground">{{ item.count }}</span>
            </FilterOptionButton>
            <span v-if="visibleSeries.length === 0" class="text-sm text-muted-foreground">
              没有匹配的本地系列。
            </span>
          </CollapsibleFilterOptions>
        </div>
      </section>
    </div>
  </Dialog>
</template>

<style scoped>
.filter-row {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  align-items: start;
  gap: 1rem;
}

.filter-row-title {
  padding-top: 0.45rem;
  color: var(--muted-foreground);
  font-size: 0.75rem;
  font-weight: 600;
}

@media (max-width: 39.999rem) {
  .filter-row {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .filter-row-title {
    padding-top: 0;
  }
}
</style>
