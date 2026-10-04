<script setup lang="ts">
import { useRouter } from 'vue-router'

import { artworkTypeLabel } from '@/features/artworks/artwork'
import type { ArtworkDetail } from '@/features/gallery/gallery-api'
import SafeHtml from '@/pages/artworks/SafeHtml.vue'
import Card from '@ui/Card.vue'

defineProps<{ artwork: ArtworkDetail }>()
const router = useRouter()

function filterByTag(tagId: number) {
  void router.push({ path: '/gallery', query: { tagId: String(tagId) } })
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
          v-if="artwork.xRestrict > 0"
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

    <SafeHtml
      v-if="artwork.description"
      class="mt-5 text-sm leading-7"
      :html="artwork.description"
    />
    <p v-else class="mt-5 text-sm text-muted-foreground">作者没有为这件作品添加说明。</p>

    <div v-if="artwork.tags.length" class="mt-5 border-t pt-4">
      <h3 class="mb-2 text-xs font-medium text-muted-foreground">标签</h3>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="tag in artwork.tags"
          :key="tag.tagId"
          type="button"
          :class="[
            'inline-flex cursor-pointer items-center gap-[0.35rem] rounded-full',
            'bg-secondary px-[0.7rem] py-[0.35rem] text-xs text-secondary-foreground',
            'transition-colors hover:bg-accent hover:text-accent-foreground',
          ]"
          @click="filterByTag(tag.tagId)"
        >
          <span>{{ tag.name }}</span>
        </button>
      </div>
    </div>
  </Card>
</template>
