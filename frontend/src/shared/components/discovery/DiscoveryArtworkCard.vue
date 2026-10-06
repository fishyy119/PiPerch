<script setup lang="ts">
import { ImageDown, ImageMinus, ImagePlus } from '@lucide/vue'
import { useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import { type DiscoveryItem, listArtworkPreviewUrls } from '@/features/discovery/discovery-api'
import ArtworkCard from '@/shared/components/artworks/ArtworkCard.vue'

const props = withDefaults(
  defineProps<{
    artwork: DiscoveryItem
    selected: boolean
    showAuthor?: boolean
  }>(),
  { showAuthor: true },
)

const emit = defineEmits<{
  toggle: [item: DiscoveryItem]
}>()

const queryClient = useQueryClient()
const target = computed<ArtworkCardTarget>(() => ({
  kind: 'external',
  href: `https://www.pixiv.net/artworks/${String(props.artwork.artworkId)}`,
}))

async function resolvePreviewUrl(pageIndex: number) {
  const urls = await queryClient.query({
    queryKey: ['discovery-artwork-preview', props.artwork.artworkId],
    queryFn: () => listArtworkPreviewUrls(props.artwork.artworkId),
    retry: false,
    staleTime: 'static',
  })
  return urls[pageIndex] ?? null
}
</script>

<template>
  <ArtworkCard
    :title="artwork.title"
    :author-name="artwork.authorName"
    :page-count="artwork.pageCount"
    :thumbnail-url="artwork.thumbnailUrl"
    :target="target"
    :resolve-preview-url="resolvePreviewUrl"
    :selected="selected"
    :show-author="showAuthor"
  >
    <template #trailing-action>
      <button
        v-if="!artwork.inLibrary"
        type="button"
        :class="[
          'group/queue absolute right-2 bottom-2 z-10 inline-flex size-10 items-center justify-center rounded-xl',
          'cursor-pointer shadow-sm ring-1 ring-transparent backdrop-blur-sm transition',
          'opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100',
          selected
            ? 'bg-primary/15 text-primary ring-primary/25 sm:opacity-100'
            : 'bg-overlay/65 text-overlay-foreground',
          selected
            ? 'hover:bg-destructive/10 hover:text-destructive hover:ring-destructive/25 focus-visible:bg-destructive/10 focus-visible:text-destructive focus-visible:ring-destructive/25'
            : 'hover:bg-primary/15 hover:text-primary hover:ring-primary/25 focus-visible:bg-primary/15 focus-visible:text-primary focus-visible:ring-primary/25',
        ]"
        :title="selected ? '从待提交队列移除' : '加入待提交队列'"
        @click.prevent.stop="emit('toggle', artwork)"
      >
        <ImagePlus v-if="!selected" :size="20" />
        <ImageDown
          v-else
          class="group-hover/queue:hidden group-focus-visible/queue:hidden"
          :size="20"
        />
        <ImageMinus
          v-if="selected"
          class="hidden group-hover/queue:block group-focus-visible/queue:block"
          :size="20"
        />
      </button>
      <!-- TODO: 此状态不会动态同步 -->
      <span
        v-else
        class="absolute right-2 bottom-2 z-10 rounded-lg bg-success px-2 py-1 text-xs font-medium text-success-foreground shadow-sm"
      >
        已在图库
      </span>
    </template>
  </ArtworkCard>
</template>
