<script setup lang="ts">
import { ExternalLink, UserRound } from '@lucide/vue'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { artworkTypeLabel } from '@/features/artworks/artwork'
import { getUserProfile, type UserProfile, userProfileKey } from '@/features/authors/author-api'
import AuthorFollowButton from '@/features/authors/AuthorFollowButton.vue'
import AuthorIdButton from '@/features/authors/AuthorIdButton.vue'
import type { ArtworkDetail } from '@/features/gallery/gallery-api'
import Card from '@ui/Card.vue'

const props = defineProps<{ artwork: ArtworkDetail }>()

const router = useRouter()
const queryClient = useQueryClient()
const authorAvatarFailed = ref(false)
const authorProfileQuery = useQuery({
  queryKey: computed(() => userProfileKey(props.artwork.authorId)),
  queryFn: () => getUserProfile(props.artwork.authorId),
})

watch(
  () => props.artwork.artworkId,
  () => {
    authorAvatarFailed.value = false
  },
)

function updateAuthorFollowState(followed: boolean) {
  queryClient.setQueryData<UserProfile>(userProfileKey(props.artwork.authorId), (profile) =>
    profile ? { ...profile, isFollowed: followed } : profile,
  )
}

function filterAuthor() {
  void router.push({
    path: '/gallery',
    query: { authorId: String(props.artwork.authorId) },
  })
}

function filterSeries() {
  if (props.artwork.seriesId === null) return
  void router.push({
    path: '/gallery',
    query: { seriesId: String(props.artwork.seriesId) },
  })
}

function formatDate(value: string | null) {
  if (!value) return '未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}
</script>

<template>
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
          :user-id="artwork.authorId"
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
        @click="filterAuthor"
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
          <strong class="block truncate text-sm transition group-hover:text-primary">
            {{ artwork.authorName }}
          </strong>
          <span class="mt-0.5 block text-xs text-muted-foreground">查看本地作品</span>
        </span>
      </button>
      <div class="mt-2 flex items-center justify-between gap-3 px-2 text-xs text-muted-foreground">
        <AuthorIdButton :user-id="artwork.authorId" />
        <a
          class="inline-flex items-center gap-1 transition hover:text-primary"
          :href="`https://www.pixiv.net/users/${String(artwork.authorId)}`"
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
          <dd>{{ artwork.artworkId }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">类型</dt>
          <dd>{{ artworkTypeLabel(artwork.artworkType) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">尺寸</dt>
          <dd>{{ artwork.width ?? '未知' }} × {{ artwork.height ?? '未知' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">页数</dt>
          <dd>{{ artwork.pageCount }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">发布时间</dt>
          <dd class="text-right">{{ formatDate(artwork.publishedAt) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-muted-foreground">下载时间</dt>
          <dd class="text-right">{{ formatDate(artwork.downloadedAt) }}</dd>
        </div>
        <div v-if="artwork.seriesId" class="flex justify-between gap-3">
          <dt class="shrink-0 text-muted-foreground">所属系列</dt>
          <dd class="min-w-0 text-right">
            <button
              type="button"
              class="cursor-pointer text-primary hover:underline"
              @click="filterSeries"
            >
              {{ artwork.seriesTitle || `系列 #${String(artwork.seriesId)}` }}
            </button>
          </dd>
        </div>
      </dl>
    </Card>
  </aside>
</template>
