<script setup lang="ts">
import { Heart } from '@lucide/vue'
import { computed, ref } from 'vue'

import type { ArtworkCardTarget } from '@/features/artworks/artwork-card'
import ArtworkCard from '@/features/artworks/ArtworkCard.vue'
import type { ArtworkSummary, FavoriteGroup } from '@/features/gallery/gallery-api'
import { galleryNavigationRouteState } from '@/features/gallery/gallery-navigation'
import Checkbox from '@ui/Checkbox.vue'
import ContextMenu, { type ContextMenuOption } from '@ui/ContextMenu.vue'

const props = defineProps<{
  artwork: ArtworkSummary
  favoriteGroups: FavoriteGroup[]
  selected: boolean
  selectionMode: boolean
  showTitle: boolean
  showAuthor: boolean
  showFavoriteIndicator: boolean
  navigationArtworkIds: readonly number[]
}>()

const emit = defineEmits<{
  toggleSelection: [artworkId: number]
  filterAuthor: [authorId: number]
  toggleFavorite: [artwork: ArtworkSummary]
  changeFavoriteGroup: [artwork: ArtworkSummary, groupId: number, mode: 'add' | 'remove']
  addToNewFavoriteGroup: [artwork: ArtworkSummary]
  syncFavorite: [artwork: ArtworkSummary]
}>()

const target = computed<ArtworkCardTarget>(() => ({
  kind: 'route',
  to: {
    path: `/artworks/${String(props.artwork.artworkId)}`,
    state: galleryNavigationRouteState(props.navigationArtworkIds),
  },
}))
const contextMenuOpen = ref(false)
const thumbnailUrl = computed(() => `/api/artworks/${String(props.artwork.artworkId)}/thumbnail`)
const availableGroups = computed(() =>
  props.favoriteGroups.filter((group) => !props.artwork.favoriteGroupIds.includes(group.groupId)),
)
const currentGroups = computed(() =>
  props.favoriteGroups.filter((group) => props.artwork.favoriteGroupIds.includes(group.groupId)),
)
const contextItems = computed<ContextMenuOption[]>(() => [
  {
    value: 'favorite',
    label: props.artwork.isFavorite ? '取消收藏' : '收藏',
  },
  {
    value: 'add-group',
    label: '添加到分组',
    children: [
      {
        value: 'add-group:new',
        label: '添加到新分组',
      },
      ...availableGroups.value.map((group, index) => ({
        value: `add-group:${String(group.groupId)}`,
        label: group.name,
        separatorBefore: index === 0,
      })),
    ],
  },
  ...(currentGroups.value.length === 0
    ? []
    : [
        {
          value: 'remove-group',
          label: '移除出分组',
          children: currentGroups.value.map((group) => ({
            value: `remove-group:${String(group.groupId)}`,
            label: group.name,
          })),
        },
      ]),
  { value: 'sync', label: '同步到 Pixiv', separatorBefore: true },
])

function resolvePreviewUrl(pageIndex: number) {
  return props.artwork.artworkType === 'ugoira'
    ? `/api/artworks/${String(props.artwork.artworkId)}/cover`
    : `/api/artworks/${String(props.artwork.artworkId)}/pages/${String(pageIndex)}`
}

function handleCardClick(event: MouseEvent) {
  if (!props.selectionMode) return

  event.preventDefault()
  event.stopPropagation()
  emit('toggleSelection', props.artwork.artworkId)
}

function handleContextAction(action: string) {
  if (action === 'favorite') emit('toggleFavorite', props.artwork)
  else if (action === 'sync') emit('syncFavorite', props.artwork)
  else if (action === 'add-group:new') emit('addToNewFavoriteGroup', props.artwork)
  else if (action.startsWith('add-group:')) {
    emit('changeFavoriteGroup', props.artwork, Number(action.slice('add-group:'.length)), 'add')
  } else if (action.startsWith('remove-group:')) {
    emit(
      'changeFavoriteGroup',
      props.artwork,
      Number(action.slice('remove-group:'.length)),
      'remove',
    )
  }
}
</script>

<template>
  <ContextMenu v-model:open="contextMenuOpen" :items="contextItems" @select="handleContextAction">
    <ArtworkCard
      :class="{ 'cursor-pointer': selectionMode }"
      :title="artwork.title"
      :author-name="artwork.authorName"
      :page-count="artwork.pageCount"
      :thumbnail-url="thumbnailUrl"
      :target="target"
      :resolve-preview-url="resolvePreviewUrl"
      :selected="selected"
      :show-title="showTitle"
      :show-author="showAuthor"
      :show-page-preview="!selectionMode && !contextMenuOpen"
      @click.capture="handleCardClick"
    >
      <template
        v-if="selectionMode || (artwork.isFavorite && showFavoriteIndicator)"
        #leading-action
      >
        <Checkbox
          v-if="selectionMode"
          :class="[
            'absolute top-2 left-2 z-10 size-5',
            'border-overlay-foreground/80 bg-overlay/55 shadow-sm backdrop-blur-sm transition',
          ]"
          :model-value="selected"
          @click.stop
          @update:model-value="emit('toggleSelection', artwork.artworkId)"
        />
        <span
          v-else
          class="pointer-events-none absolute top-2 left-2 z-10 grid size-7 place-items-center rounded-full bg-overlay/60 text-white shadow-sm backdrop-blur-sm"
        >
          <Heart :size="16" fill="currentColor" />
        </span>
      </template>

      <template #author>
        <button
          type="button"
          :class="[
            'block max-w-full cursor-pointer truncate text-left text-xs text-muted-foreground hover:text-primary',
            showTitle ? 'mt-0.5' : '',
          ]"
          @click="emit('filterAuthor', artwork.authorId)"
        >
          {{ artwork.authorName }}
        </button>
      </template>
    </ArtworkCard>
  </ContextMenu>
</template>
