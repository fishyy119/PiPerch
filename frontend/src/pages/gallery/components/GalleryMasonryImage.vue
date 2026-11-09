<script setup lang="ts">
import { ImageOff } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { GalleryMediaItem } from '@/features/gallery/gallery-media'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import { ManagedImage } from '@ui/image'

const props = defineProps<{
  item: GalleryMediaItem
  navigationArtworkIds: readonly number[]
}>()
const imageFailed = ref(false)
const target = computed(() => ({
  path: `/artworks/${String(props.item.artwork.localArtworkId)}`,
  state: galleryNavigationRouteState(props.navigationArtworkIds),
}))
const imageUrl = computed(() => {
  const media = props.item.media
  const base = `/api/artworks/${String(media.artworkId)}`
  return media.role === 'ugoira' ? `${base}/ugoira` : `${base}/pages/${String(media.pageIndex)}`
})
watch(imageUrl, () => {
  imageFailed.value = false
})
</script>

<template>
  <RouterLink
    :to="target"
    class="relative block overflow-hidden rounded-sm bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    :style="{ aspectRatio: item.aspectRatio }"
  >
    <ManagedImage
      v-if="!imageFailed"
      class="block size-full object-contain"
      :src="imageUrl"
      :alt="item.artwork.title"
      loading="eager"
      @error="imageFailed = true"
    />
    <ImageOff v-else class="absolute inset-0 m-auto text-muted-foreground" :size="28" />
  </RouterLink>
</template>
