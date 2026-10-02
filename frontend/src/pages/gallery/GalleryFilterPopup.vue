<script setup lang="ts">
import { ArrowDown, ArrowUp } from '@lucide/vue'
import { computed, ref } from 'vue'

import type { NamedCount, Tag } from '@/features/gallery/gallery-api'
import CollapsibleFilterOptions from '@/pages/gallery/CollapsibleFilterOptions.vue'
import FilterOptionButton from '@/pages/gallery/FilterOptionButton.vue'
import Button from '@ui/Button.vue'
import Dialog from '@ui/Dialog.vue'
import SearchInput from '@ui/SearchInput.vue'

type FilterName = 'authorId' | 'seriesId' | 'artworkType' | 'rating' | 'ai'

const props = defineProps<{
  open: boolean
  tags: Tag[]
  authors: NamedCount[]
  series: NamedCount[]
  selectedTagIds: number[]
  authorId: number | undefined
  seriesId: number | undefined
  artworkType: string
  rating: string
  ai: string
  sort: string
  order: string
  authorSearch: string
  seriesSearch: string
}>()

const emit = defineEmits<{
  close: []
  toggleTag: [tagId: number]
  updateFilter: [name: FilterName, value: string | undefined]
  updateSort: [sort: string, order: string]
  updateAuthorSearch: [value: string]
  updateSeriesSearch: [value: string]
}>()

const tagSearch = ref('')
const visibleTags = computed(() => {
  const needle = tagSearch.value.trim().toLocaleLowerCase()
  return props.tags.filter((tag) => {
    if (!needle) return true
    return [tag.name, tag.translatedName ?? ''].some((name) =>
      name.toLocaleLowerCase().includes(needle),
    )
  })
})
</script>

<template>
  <Dialog
    :open="open"
    position="top"
    title="筛选本地作品"
    title-class="mb-5"
    content-class="p-4 sm:p-6 lg:left-60"
    overlay-class="top-16 lg:left-60"
    @update:open="!$event && emit('close')"
  >
    <div class="grid gap-x-6 gap-y-5">
      <section class="filter-row">
        <div class="filter-row-title flex items-center gap-1">
          <h3>排序</h3>
          <Button
            variant="ghost"
            size="iconSmall"
            class="-my-1 shrink-0 rounded-full text-muted-foreground"
            @click="emit('updateSort', sort, order === 'desc' ? 'asc' : 'desc')"
          >
            <ArrowDown v-if="order === 'desc'" :size="15" />
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
            ]"
            :key="option.value"
            :active="sort === option.value"
            @click="emit('updateSort', option.value, order)"
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
            :active="artworkType === option.value"
            @click="emit('updateFilter', 'artworkType', option.value || undefined)"
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
            :active="rating === option.value"
            @click="emit('updateFilter', 'rating', option.value)"
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
            :active="ai === option.value"
            @click="emit('updateFilter', 'ai', option.value)"
          >
            {{ option.label }}
          </FilterOptionButton>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <h3 class="filter-row-title">标签</h3>
        <div>
          <SearchInput v-model="tagSearch" class="mb-3 w-full max-w-sm" placeholder="搜索标签…" />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-for="tag in visibleTags"
              :key="tag.tagId"
              :active="selectedTagIds.includes(tag.tagId)"
              @click="emit('toggleTag', tag.tagId)"
            >
              {{ tag.translatedName || tag.name }}
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
            :model-value="authorSearch"
            class="mb-3 w-full max-w-sm"
            placeholder="搜索作者…"
            @update:model-value="emit('updateAuthorSearch', $event)"
          />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-if="authorId && !authors.some((item) => item.itemId === authorId)"
              :active="true"
              @click="emit('updateFilter', 'authorId', undefined)"
            >
              作者 #{{ authorId }}
            </FilterOptionButton>
            <FilterOptionButton
              v-for="author in authors"
              :key="author.itemId"
              :active="authorId === author.itemId"
              @click="
                emit(
                  'updateFilter',
                  'authorId',
                  authorId === author.itemId ? undefined : String(author.itemId),
                )
              "
            >
              {{ author.name }}
              <span class="text-xs text-muted-foreground">{{ author.count }}</span>
            </FilterOptionButton>
            <span v-if="authors.length === 0" class="text-sm text-muted-foreground">
              没有匹配的本地作者。
            </span>
          </CollapsibleFilterOptions>
        </div>
      </section>

      <section class="filter-row border-t pt-5">
        <h3 class="filter-row-title">系列</h3>
        <div>
          <SearchInput
            :model-value="seriesSearch"
            class="mb-3 w-full max-w-sm"
            placeholder="搜索系列…"
            @update:model-value="emit('updateSeriesSearch', $event)"
          />
          <CollapsibleFilterOptions>
            <FilterOptionButton
              v-if="seriesId && !series.some((item) => item.itemId === seriesId)"
              :active="true"
              @click="emit('updateFilter', 'seriesId', undefined)"
            >
              系列 #{{ seriesId }}
            </FilterOptionButton>
            <FilterOptionButton
              v-for="item in series"
              :key="item.itemId"
              :active="seriesId === item.itemId"
              @click="
                emit(
                  'updateFilter',
                  'seriesId',
                  seriesId === item.itemId ? undefined : String(item.itemId),
                )
              "
            >
              {{ item.name }} <span class="text-xs text-muted-foreground">{{ item.count }}</span>
            </FilterOptionButton>
            <span v-if="series.length === 0" class="text-sm text-muted-foreground">
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
