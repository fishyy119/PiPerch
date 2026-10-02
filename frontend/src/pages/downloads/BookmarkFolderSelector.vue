<script setup lang="ts">
import { Check, LockKeyhole } from '@lucide/vue'

import type { BookmarkFolder, BookmarkFolderReference } from '@/features/discovery/discovery-api'

const props = defineProps<{
  folders: readonly BookmarkFolder[]
  selectedFolders: readonly BookmarkFolderReference[]
}>()

const emit = defineEmits<{
  'update:selectedFolders': [folders: BookmarkFolderReference[]]
}>()

function folderKey(folder: BookmarkFolderReference) {
  return JSON.stringify([folder.visibility, folder.tag])
}

function isSelected(folder: BookmarkFolderReference) {
  const key = folderKey(folder)
  return props.selectedFolders.some((selected) => folderKey(selected) === key)
}

function toggleFolder(folder: BookmarkFolder) {
  const key = folderKey(folder)
  const selected = props.selectedFolders.some((item) => folderKey(item) === key)
  let next = props.selectedFolders.filter((item) => folderKey(item) !== key)
  if (!selected) {
    next = next.filter((item) => {
      if (item.visibility !== folder.visibility) return true
      return folder.kind === 'all' ? false : item.tag !== null
    })
    next.push({ visibility: folder.visibility, tag: folder.tag })
  }
  const selectedKeys = new Set(next.map(folderKey))
  emit(
    'update:selectedFolders',
    props.folders
      .filter((item) => selectedKeys.has(folderKey(item)))
      .map((item) => ({ visibility: item.visibility, tag: item.tag })),
  )
}
</script>

<template>
  <div class="grid grid-cols-[repeat(auto-fit,minmax(min(100%,13rem),1fr))] gap-2">
    <button
      v-for="folder in folders"
      :key="folderKey(folder)"
      type="button"
      :class="[
        'flex min-w-0 cursor-pointer items-center gap-2.5 rounded-xl border p-3 text-left transition',
        'hover:border-primary/50 hover:bg-accent',
        isSelected(folder) ? 'border-primary bg-accent ring-1 ring-primary' : '',
      ]"
      :title="`${folder.visibility === 'public' ? '公开收藏' : '非公开收藏'} / ${folder.name}`"
      @click="toggleFolder(folder)"
    >
      <span
        class="grid size-5 shrink-0 place-items-center rounded-md border border-input bg-background"
        :class="isSelected(folder) ? 'border-primary bg-primary text-primary-foreground' : ''"
      >
        <Check v-if="isSelected(folder)" :size="13" :stroke-width="3" />
      </span>
      <span class="min-w-0 flex-1 truncate text-sm font-medium">{{ folder.name }}</span>
      <span class="shrink-0 text-xs text-muted-foreground">{{ folder.itemCount }}</span>
      <LockKeyhole
        v-if="folder.visibility === 'private'"
        class="shrink-0 text-muted-foreground"
        :size="15"
      />
    </button>
  </div>
</template>
