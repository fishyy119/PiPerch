<script setup lang="ts">
import { ImageOff } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  type ArtworkCardTarget,
  type ArtworkPreviewUrlResolver,
} from '@/features/artworks/artwork-card'
import ArtworkPagePreview from '@/shared/components/artworks/ArtworkPagePreview.vue'
import SmartCropImage from '@ui/SmartCropImage.vue'

const props = withDefaults(
  defineProps<{
    title: string
    authorName: string
    pageCount: number
    thumbnailUrl: string | null
    target: ArtworkCardTarget
    resolvePreviewUrl: ArtworkPreviewUrlResolver
    selected?: boolean
    showTitle?: boolean
    showAuthor?: boolean
    showPagePreview?: boolean
  }>(),
  { selected: false, showTitle: true, showAuthor: true, showPagePreview: true },
)

const thumbnailFailed = ref(false)
const linkComponent = computed(() => (props.target.kind === 'route' ? RouterLink : 'a'))
const linkAttributes = computed(() =>
  props.target.kind === 'route'
    ? { to: props.target.to }
    : { href: props.target.href, target: '_blank', rel: 'noreferrer' },
)

watch(
  () => props.thumbnailUrl,
  () => {
    thumbnailFailed.value = false
  },
)
</script>

<template>
  <article
    class="min-w-0 rounded-xl ring-primary transition"
    :class="selected ? 'bg-primary ring-3' : 'ring-0'"
  >
    <div
      class="group relative aspect-square overflow-hidden bg-muted"
      :class="selected && (showTitle || showAuthor) ? 'rounded-t-xl' : 'rounded-xl'"
    >
      <component
        :is="linkComponent"
        v-bind="linkAttributes"
        class="block size-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <SmartCropImage
          v-if="thumbnailUrl && !thumbnailFailed"
          class="size-full object-cover transition duration-300 hover:scale-[1.025]"
          :src="thumbnailUrl"
          :alt="title"
          loading="lazy"
          @error="thumbnailFailed = true"
        />
        <ImageOff v-else class="absolute inset-0 m-auto text-muted-foreground" :size="28" />
      </component>

      <slot name="leading-action" />
      <ArtworkPagePreview
        v-if="showPagePreview"
        :title="title"
        :page-count="pageCount"
        :resolve-url="resolvePreviewUrl"
      />
      <slot name="trailing-action" />
    </div>

    <div
      v-if="showTitle || showAuthor"
      class="rounded-b-xl p-2.5"
      :class="selected ? 'text-primary-foreground' : ''"
    >
      <component
        :is="linkComponent"
        v-if="showTitle"
        v-bind="linkAttributes"
        class="block truncate text-sm font-semibold transition-colors"
        :class="selected ? '' : 'hover:text-primary'"
      >
        {{ title }}
      </component>
      <slot v-if="showAuthor" name="author" :author-name="authorName" :selected="selected">
        <span
          class="mt-0.5 block truncate text-xs transition-colors"
          :class="selected ? '' : 'text-muted-foreground'"
        >
          {{ authorName }}
        </span>
      </slot>
    </div>
  </article>
</template>
