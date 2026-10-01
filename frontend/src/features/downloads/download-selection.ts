import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { DiscoveryItem } from './download-api'

export interface DownloadSelectionEntry {
  artworkId: number
  item: DiscoveryItem | null
}

export const useDownloadSelection = defineStore('download-selection', () => {
  const ids = ref(new Set<number>())
  const itemCache = ref(new Map<number, DiscoveryItem>())
  const selectedIds = computed(() => [...ids.value])
  const selectedEntries = computed<DownloadSelectionEntry[]>(() =>
    selectedIds.value.map((artworkId) => ({
      artworkId,
      item: itemCache.value.get(artworkId) ?? null,
    })),
  )

  function remember(items: readonly DiscoveryItem[]) {
    if (items.length === 0) return
    const next = new Map(itemCache.value)
    items.forEach((item) => next.set(item.artworkId, item))
    itemCache.value = next
  }

  function toggle(item: DiscoveryItem) {
    remember([item])
    const next = new Set(ids.value)
    if (next.has(item.artworkId)) next.delete(item.artworkId)
    else next.add(item.artworkId)
    ids.value = next
  }

  function addAll(candidates: readonly DiscoveryItem[]) {
    remember(candidates)
    addIds(candidates.map((item) => item.artworkId))
  }

  function removeAll(candidates: readonly DiscoveryItem[]) {
    removeIds(candidates.map((item) => item.artworkId))
  }

  function addIds(artworkIds: readonly number[]) {
    ids.value = new Set([...ids.value, ...artworkIds])
  }

  function removeIds(artworkIds: readonly number[]) {
    const next = new Set(ids.value)
    artworkIds.forEach((artworkId) => next.delete(artworkId))
    ids.value = next
  }

  function clear() {
    ids.value = new Set()
  }

  return {
    selectedIds,
    selectedEntries,
    remember,
    toggle,
    addAll,
    removeAll,
    addIds,
    removeIds,
    clear,
  }
})
