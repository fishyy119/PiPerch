<script setup lang="ts">
import { useRouter } from 'vue-router'

import { artworkTypeLabel } from '@/features/artworks/artwork'
import type { ArtworkDetail } from '@/features/artworks/artworks-api'
import SafeDescription from '@/pages/artworks/SafeDescription.vue'
import { writeToClipboard } from '@/shared/lib/clipboard'
import { Card } from '@ui/card'
import { cn } from '@ui/cn'

defineProps<{ artwork: ArtworkDetail }>()
const router = useRouter()
const capsuleClasses = cn(
  'inline-flex cursor-pointer items-center gap-[0.35rem] rounded-full',
  'px-[0.7rem] py-[0.35rem] text-xs',
  'text-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
)

function filterByTag(tagId: number) {
  void router.push({ path: '/gallery', query: { tagId: String(tagId) } })
}

function filterByGroup(groupId: number) {
  void router.push({ path: '/gallery', query: { groupId: String(groupId) } })
}
</script>

<template>
  <Card as="section" class="p-5 sm:p-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <h2 class="min-w-0 text-xl font-semibold sm:text-2xl">
        {{ artwork.title }}
      </h2>
      <div class="flex flex-wrap gap-1.5">
        <span class="rounded-lg bg-muted px-[0.55rem] py-[0.3rem] text-xs text-muted-foreground">
          {{ artworkTypeLabel(artwork.artworkType) }}
        </span>
        <span
          v-if="(artwork.xRestrict ?? 0) > 0"
          class="rounded-lg bg-muted px-[0.55rem] py-[0.3rem] text-xs text-destructive!"
        >
          R18
        </span>
        <span
          v-if="artwork.isAi"
          class="rounded-lg bg-muted px-[0.55rem] py-[0.3rem] text-xs text-muted-foreground"
        >
          AI 生成
        </span>
      </div>
    </div>

    <SafeDescription
      v-if="artwork.description"
      class="mt-5 text-sm leading-7"
      :html="artwork.description"
      :links="artwork.artworkLinks"
    />
    <p v-else class="mt-5 text-sm text-muted-foreground">作者没有为这件作品添加说明。</p>

    <div v-if="artwork.tags.length || artwork.groups.length" class="mt-5 border-t pt-4">
      <h3 class="mb-2 text-xs font-medium text-muted-foreground">标签</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="tag in artwork.tags"
          :key="tag.tagId"
          type="button"
          :class="cn(capsuleClasses, 'bg-muted')"
          @click="filterByTag(tag.tagId)"
          @contextmenu.prevent="writeToClipboard(tag.name)"
        >
          <span>{{ tag.name }}</span>
        </button>
        <button
          v-for="group in artwork.groups"
          :key="group.groupId"
          type="button"
          :class="cn(capsuleClasses, 'bg-primary/20')"
          @click="filterByGroup(group.groupId)"
          @contextmenu.prevent="writeToClipboard(group.name)"
        >
          <span>{{ group.name }}</span>
        </button>
      </div>
    </div>
  </Card>
</template>
