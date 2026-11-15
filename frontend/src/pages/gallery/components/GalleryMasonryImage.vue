<script setup lang="ts">
import { ImageOff } from '@lucide/vue'
import { computed, ref, watch } from 'vue'

import { artworkMediaUrl } from '@/features/artworks/artwork'
import type { GalleryMediaItem } from '@/features/gallery/gallery-media'
import { Button } from '@ui/button'
import { ManagedImage } from '@ui/image'

const props = defineProps<{
  item: GalleryMediaItem
}>()
const emit = defineEmits<{
  open: []
}>()
const imageFailed = ref(false)
const imageUrl = computed(() =>
  artworkMediaUrl(
    props.item.media.artworkId,
    props.item.artwork.artworkType,
    props.item.media.pageIndex ?? 0,
  ),
)
watch(imageUrl, () => {
  imageFailed.value = false
})
</script>

<template>
  <Button
    variant="blank"
    class="relative block w-full overflow-hidden rounded-sm bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    :style="{ aspectRatio: item.aspectRatio }"
    @click="emit('open')"
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
  </Button>
</template>
