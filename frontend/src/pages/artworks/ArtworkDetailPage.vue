<script setup lang="ts">
import {
  ChevronDown,
  ChevronUp,
  Download,
  ExternalLink,
  Images,
  Trash2,
  UserRound,
} from '@lucide/vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { usePreference } from '@/app/usePreference'
import { getUserProfile, type UserProfile, userProfileKey } from '@/features/authors/author-api'
import AuthorFollowButton from '@/features/authors/AuthorFollowButton.vue'
import AuthorIdButton from '@/features/authors/AuthorIdButton.vue'
import { deleteArtwork, getArtwork, listRelatedArtworks } from '@/features/gallery/gallery-api'
import {
  galleryNavigationRouteState,
  type GalleryNavigationState,
  parseGalleryNavigationState,
} from '@/features/gallery/gallery-navigation'
import SafeHtml from '@/pages/artworks/SafeHtml.vue'
import { usePageKeyboardShortcuts } from '@/shared/lib/usePageKeyboardShortcuts'
import Button from '@ui/Button.vue'
import Card from '@ui/Card.vue'
import ConfirmDialog from '@ui/ConfirmDialog.vue'
import LightboxGallery, { type LightboxItem } from '@ui/LightboxGallery.vue'
import SettingsPopover from '@ui/SettingsPopover.vue'
import Slider from '@ui/Slider.vue'
import SmartCropImage from '@ui/SmartCropImage.vue'

const PAGE_SELECTOR_ITEM_SIZE_PX = 80
const PAGE_SELECTOR_GAP_PX = 8

const route = useRoute()
const router = useRouter()
const queryClient = useQueryClient()
const artworkId = computed(() => Number(route.params.artworkId))
const galleryNavigation = ref<GalleryNavigationState | null>(
  parseGalleryNavigationState(router.options.history.state),
)
const selectedPage = ref<number | null>(null)
const pageSelectorExpanded = ref(false)
const pageSelectorGrid = ref<HTMLElement | null>(null)
const pageSelectorColumns = ref(Number.POSITIVE_INFINITY)
const deleteOpen = ref(false)
const authorAvatarFailed = ref(false)
const relatedCardWidth = usePreference('artworkDetail.relatedCardWidth')

const artworkQuery = useQuery({
  queryKey: computed(() => ['artwork', artworkId.value]),
  queryFn: () => getArtwork(artworkId.value),
  placeholderData: (previousData) => previousData,
})
const relatedQuery = useQuery({
  queryKey: computed(() => ['related-artworks', artworkId.value]),
  queryFn: () => listRelatedArtworks(artworkId.value),
})
const authorId = computed(() => artworkQuery.data.value?.authorId)
const authorProfileQuery = useQuery({
  queryKey: computed(() => userProfileKey(authorId.value ?? 0)),
  queryFn: () => {
    if (authorId.value === undefined) throw new Error('作品缺少作者 ID。')
    return getUserProfile(authorId.value)
  },
  enabled: computed(() => authorId.value !== undefined),
})
const relatedGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, ${String(relatedCardWidth.value)}px), ${String(relatedCardWidth.value)}px))`,
}))

const deleteMutation = useMutation({
  mutationFn: () => deleteArtwork(artworkQuery.data.value?.artworkId ?? artworkId.value),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['artworks'] })
    await router.replace('/gallery')
  },
})

function updateAuthorFollowState(followed: boolean) {
  const userId = authorId.value
  if (userId === undefined) return
  queryClient.setQueryData<UserProfile>(userProfileKey(userId), (profile) =>
    profile ? { ...profile, isFollowed: followed } : profile,
  )
}

const pageIndexes = computed(() => {
  const artwork = artworkQuery.data.value
  if (!artwork) return []
  return artwork.media
    .map((media) => media.pageIndex)
    .filter((page): page is number => page !== null)
    .sort((left, right) => left - right)
})
const currentPage = computed(() => selectedPage.value ?? pageIndexes.value[0] ?? null)
const previewUrl = computed(() => {
  const artwork = artworkQuery.data.value
  if (artwork?.artworkType === 'ugoira') {
    return `/api/artworks/${String(artwork.artworkId)}/cover`
  }
  return currentPage.value === null ? '' : mediaUrl(currentPage.value)
})
const lightboxItems = computed<LightboxItem[]>(() => {
  const artwork = artworkQuery.data.value
  if (!artwork) return []
  if (artwork.artworkType === 'ugoira') {
    return [{ src: previewUrl.value, alt: artwork.title }]
  }
  return pageIndexes.value.map((page, index) => ({
    src: mediaUrl(page),
    alt:
      pageIndexes.value.length > 1 ? `${artwork.title} 第 ${String(index + 1)} 页` : artwork.title,
  }))
})
const lightboxInitialIndex = computed(() => {
  if (artworkQuery.data.value?.artworkType === 'ugoira' || currentPage.value === null) return 0
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

watch(artworkId, (currentArtworkId) => {
  selectedPage.value = null
  pageSelectorExpanded.value = false
  authorAvatarFailed.value = false

  const navigation = parseGalleryNavigationState(router.options.history.state)
  galleryNavigation.value = navigation?.artworkIds.includes(currentArtworkId) ? navigation : null
})

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
  const mediaArtworkId = artworkQuery.data.value?.artworkId ?? artworkId.value
  return `/api/artworks/${String(mediaArtworkId)}/pages/${String(page)}`
}

function mediaThumbnailUrl(page: number) {
  return `${mediaUrl(page)}/thumbnail`
}

function handleLightboxIndexChange(index: number) {
  if (artworkQuery.data.value?.artworkType === 'ugoira') return
  const page = pageIndexes.value[index]
  if (page !== undefined) selectedPage.value = page
}

function selectAdjacentPage(offset: -1 | 1) {
  if (artworkQuery.data.value?.artworkType === 'ugoira') return

  const currentIndex = pageIndexes.value.indexOf(currentPage.value ?? -1)
  const nextPage = pageIndexes.value[currentIndex + offset]
  if (nextPage !== undefined) selectedPage.value = nextPage
}

function selectAdjacentArtwork(offset: -1 | 1) {
  const navigation = galleryNavigation.value
  if (navigation === null) return

  const currentIndex = navigation.artworkIds.indexOf(artworkId.value)
  if (currentIndex < 0) return

  const nextArtworkId = navigation.artworkIds[currentIndex + offset]
  if (nextArtworkId === undefined) return

  void router
    .replace({
      path: `/artworks/${String(nextArtworkId)}`,
      state: galleryNavigationRouteState(navigation.artworkIds),
    })
    .then(() => window.scrollTo({ top: 0 }))
}

usePageKeyboardShortcuts(
  (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      if (artworkQuery.data.value?.artworkType === 'ugoira' || pageIndexes.value.length <= 1) return
      event.preventDefault()
      selectAdjacentPage(event.key === 'ArrowLeft' ? -1 : 1)
      return
    }

    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
    const navigation = galleryNavigation.value
    if (!navigation?.artworkIds.includes(artworkId.value)) return

    event.preventDefault()
    selectAdjacentArtwork(event.key === 'ArrowUp' ? -1 : 1)
  },
  { allowOverlay: (overlay) => overlay.classList.contains('artwork-lightbox') },
)

function filterByTag(tagId: number) {
  void router.push({ path: '/gallery', query: { tagId: String(tagId) } })
}

function filterByAuthor() {
  const authorId = artworkQuery.data.value?.authorId
  if (authorId !== undefined) {
    void router.push({ path: '/gallery', query: { authorId: String(authorId) } })
  }
}

function filterBySeries() {
  const seriesId = artworkQuery.data.value?.seriesId
  if (seriesId !== null && seriesId !== undefined) {
    void router.push({ path: '/gallery', query: { seriesId: String(seriesId) } })
  }
}

function formatDate(value: string | null) {
  if (!value) return '未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

function typeLabel(type: string) {
  return { illust: '插画', manga: '漫画', ugoira: 'Ugoira' }[type] ?? type
}
</script>

<template>
  <div v-if="artworkQuery.isPending.value" class="py-24 text-center text-muted-foreground">
    正在读取作品…
  </div>
  <div v-else-if="artworkQuery.error.value" class="py-24 text-center text-destructive">
    {{ artworkQuery.error.value.message }}
  </div>
  <article v-else-if="artworkQuery.data.value" class="space-y-4">
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="min-w-0 space-y-5">
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
                  :alt="artworkQuery.data.value.title"
                  decoding="async"
                />
              </button>
            </div>
          </LightboxGallery>

          <div
            v-if="artworkQuery.data.value.artworkType !== 'ugoira' && pageIndexes.length > 1"
            class="border-t p-3"
          >
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
              <Button
                variant="ghost"
                size="small"
                @click="pageSelectorExpanded = !pageSelectorExpanded"
              >
                <ChevronUp v-if="pageSelectorExpanded" :size="15" />
                <ChevronDown v-else :size="15" />
                {{ pageSelectorExpanded ? '收起' : '展开全部' }}
              </Button>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3 border-t p-3 sm:p-4">
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <Images :size="17" />
              <span v-if="artworkQuery.data.value.artworkType === 'ugoira'">
                {{ artworkQuery.data.value.ugoiraFrames.length }} 帧 · 首版暂不支持播放
              </span>
              <span v-else>
                第 {{ (currentPage ?? 0) + 1 }} / {{ artworkQuery.data.value.pageCount }} 页 ·
                {{ typeLabel(artworkQuery.data.value.artworkType) }}
              </span>
            </div>
            <div class="flex flex-wrap gap-2">
              <a
                class="detail-action"
                :href="`https://www.pixiv.net/artworks/${String(artworkQuery.data.value.artworkId)}`"
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink :size="16" />Pixiv 原作
              </a>
              <a
                v-if="artworkQuery.data.value.artworkType === 'ugoira'"
                class="detail-action"
                :href="`/api/artworks/${String(artworkQuery.data.value.artworkId)}/ugoira`"
                download
              >
                <Download :size="16" />原始 ZIP
              </a>
              <a
                v-else-if="currentPage !== null"
                class="detail-action"
                :href="mediaUrl(currentPage)"
                download
              >
                <Download :size="16" />下载当前页
              </a>
              <Button variant="danger" @click="deleteOpen = true">
                <Trash2 :size="16" />永久删除
              </Button>
            </div>
          </div>
        </Card>

        <Card as="section" class="p-5 sm:p-6">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <h2 class="min-w-0 text-xl font-semibold sm:text-2xl">
              {{ artworkQuery.data.value.title }}
            </h2>
            <div class="flex flex-wrap gap-1.5">
              <span class="metadata-badge">
                {{ typeLabel(artworkQuery.data.value.artworkType) }}
              </span>
              <span
                v-if="artworkQuery.data.value.xRestrict > 0"
                class="metadata-badge text-destructive!"
              >
                R18
              </span>
              <span v-if="artworkQuery.data.value.isAi" class="metadata-badge">AI 生成</span>
            </div>
          </div>

          <SafeHtml
            v-if="artworkQuery.data.value.description"
            class="detail-description mt-5 text-sm leading-7"
            :html="artworkQuery.data.value.description"
          />
          <p v-else class="mt-5 text-sm text-muted-foreground">作者没有为这件作品添加说明。</p>

          <div v-if="artworkQuery.data.value.tags.length" class="mt-5 border-t pt-4">
            <h3 class="mb-2 text-xs font-medium text-muted-foreground">标签</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="tag in artworkQuery.data.value.tags"
                :key="tag.tagId"
                type="button"
                class="detail-tag"
                @click="filterByTag(tag.tagId)"
              >
                <span>{{ tag.translatedName || tag.name }}</span>
                <span
                  v-if="tag.translatedName && tag.translatedName !== tag.name"
                  class="text-muted-foreground"
                >
                  {{ tag.name }}
                </span>
              </button>
            </div>
          </div>
        </Card>

        <Card as="section" class="p-5 sm:p-6">
          <div class="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2 class="font-semibold">相关作品</h2>
              <p class="mt-1 text-xs text-muted-foreground">根据本地作品的作者和共享标签推荐。</p>
            </div>
            <SettingsPopover title="相关作品显示设置">
              <div class="space-y-2">
                <p class="text-sm font-medium">卡片大小</p>
                <div class="flex items-center gap-3">
                  <Slider
                    v-model="relatedCardWidth"
                    class="flex-1"
                    :min="120"
                    :max="320"
                    :step="10"
                  />
                  <output class="w-11 text-right text-xs tabular-nums">
                    {{ relatedCardWidth }}px
                  </output>
                </div>
              </div>
            </SettingsPopover>
          </div>
          <p v-if="relatedQuery.isPending.value" class="py-8 text-sm text-muted-foreground">
            正在查找相关作品…
          </p>
          <p v-else-if="relatedQuery.error.value" class="py-8 text-sm text-destructive">
            {{ relatedQuery.error.value.message }}
          </p>
          <div
            v-else-if="relatedQuery.data.value?.length"
            class="grid justify-between gap-4"
            :style="relatedGridStyle"
          >
            <RouterLink
              v-for="related in relatedQuery.data.value"
              :key="related.artworkId"
              class="group block min-w-0"
              :to="`/artworks/${String(related.artworkId)}`"
            >
              <div class="aspect-square w-full overflow-hidden rounded-xl bg-muted">
                <SmartCropImage
                  class="size-full object-cover transition duration-300 group-hover:scale-[1.025]"
                  :src="`/api/artworks/${String(related.artworkId)}/thumbnail`"
                  :alt="related.title"
                  loading="lazy"
                />
              </div>
            </RouterLink>
          </div>
          <p v-else class="py-8 text-sm text-muted-foreground">本地图库中暂无相关作品。</p>
        </Card>
      </div>

      <aside class="space-y-4 xl:sticky xl:top-20">
        <Card as="section" class="p-5">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-muted-foreground">画师</h3>
            <span v-if="authorProfileQuery.isPending.value" class="text-xs text-muted-foreground">
              查询中…
            </span>
            <span v-else-if="authorProfileQuery.error.value" class="text-xs text-muted-foreground">
              状态未知
            </span>
            <AuthorFollowButton
              v-else-if="authorProfileQuery.data.value"
              size="small"
              :user-id="artworkQuery.data.value.authorId"
              :followed="authorProfileQuery.data.value.isFollowed"
              @change="updateAuthorFollowState"
            />
          </div>
          <button
            type="button"
            :class="[
              'group mt-3 flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left',
              'cursor-pointer transition',
              'focus-visible:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
            ]"
            @click="filterByAuthor"
          >
            <span
              class="grid size-12 shrink-0 place-items-center overflow-hidden rounded-full bg-primary text-primary-foreground shadow-sm"
            >
              <img
                v-if="authorProfileQuery.data.value?.avatarUrl && !authorAvatarFailed"
                class="size-full object-cover"
                :src="authorProfileQuery.data.value.avatarUrl"
                alt=""
                loading="lazy"
                @error="authorAvatarFailed = true"
              />
              <UserRound v-else :size="22" />
            </span>
            <span class="min-w-0">
              <strong class="block truncate text-sm transition group-hover:text-primary">{{
                artworkQuery.data.value.authorName
              }}</strong>
              <span class="mt-0.5 block text-xs text-muted-foreground">查看本地作品</span>
            </span>
          </button>
          <div
            class="mt-2 flex items-center justify-between gap-3 px-2 text-xs text-muted-foreground"
          >
            <AuthorIdButton :user-id="artworkQuery.data.value.authorId" />
            <a
              class="inline-flex items-center gap-1 transition hover:text-primary"
              :href="`https://www.pixiv.net/users/${String(artworkQuery.data.value.authorId)}`"
              target="_blank"
              rel="noreferrer"
            >
              Pixiv 主页<ExternalLink :size="11" />
            </a>
          </div>
        </Card>

        <Card as="section" class="p-5">
          <h3 class="text-sm font-semibold">作品信息</h3>
          <dl class="mt-3 grid gap-3 text-sm">
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">作品 ID</dt>
              <dd>{{ artworkQuery.data.value.artworkId }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">类型</dt>
              <dd>{{ typeLabel(artworkQuery.data.value.artworkType) }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">尺寸</dt>
              <dd>
                {{ artworkQuery.data.value.width ?? '未知' }} ×
                {{ artworkQuery.data.value.height ?? '未知' }}
              </dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">页数</dt>
              <dd>{{ artworkQuery.data.value.pageCount }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">发布时间</dt>
              <dd class="text-right">{{ formatDate(artworkQuery.data.value.publishedAt) }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted-foreground">下载时间</dt>
              <dd class="text-right">{{ formatDate(artworkQuery.data.value.downloadedAt) }}</dd>
            </div>
            <div v-if="artworkQuery.data.value.seriesId" class="flex justify-between gap-3">
              <dt class="shrink-0 text-muted-foreground">所属系列</dt>
              <dd class="min-w-0 text-right">
                <button
                  type="button"
                  class="cursor-pointer text-primary hover:underline"
                  @click="filterBySeries"
                >
                  {{
                    artworkQuery.data.value.seriesTitle ||
                    `系列 #${String(artworkQuery.data.value.seriesId)}`
                  }}
                </button>
              </dd>
            </div>
          </dl>
        </Card>
      </aside>
    </div>

    <ConfirmDialog
      :open="deleteOpen"
      title="永久删除作品"
      description="作品记录和本地文件将被永久删除，此操作无法撤销。"
      confirm-text="永久删除"
      :busy="deleteMutation.isPending.value"
      @close="deleteOpen = false"
      @confirm="deleteMutation.mutate()"
    />
  </article>
</template>

<style scoped>
.detail-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  border-radius: 9999px;
  color: var(--secondary-foreground);
  background: var(--secondary);
  padding: 0.35rem 0.7rem;
  font-size: 0.75rem;
  transition:
    color 150ms,
    background-color 150ms;
}

.detail-tag:hover {
  color: var(--accent-foreground);
  background: var(--accent);
}

.detail-action {
  display: inline-flex;
  min-height: 2.5rem;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--card-foreground);
  background: var(--card);
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition:
    border-color 150ms,
    color 150ms,
    background-color 150ms;
}

.detail-action:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.metadata-badge {
  border-radius: 0.5rem;
  background: var(--muted);
  padding: 0.3rem 0.55rem;
  color: var(--muted-foreground);
  font-size: 0.75rem;
}

.detail-description :deep(a) {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 0.15rem;
}

.detail-description :deep(p) {
  margin-block: 0.5rem;
}
</style>
