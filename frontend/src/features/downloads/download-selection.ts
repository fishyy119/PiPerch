import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import { useLibraryMembershipStore } from '@/features/library/library-membership'

export interface DownloadSelectionEntry {
  artworkId: number
  item: DiscoveryItem | null
}

export const useDownloadSelection = defineStore('download-selection', () => {
  const library = useLibraryMembershipStore()
  const ids = ref(new Set<number>())
  const itemCache = ref(new Map<number, DiscoveryItem>())
  const selectedIds = computed(() => [...ids.value])
  const selectedEntries = computed<DownloadSelectionEntry[]>(() =>
    selectedIds.value.map((artworkId) => ({
      artworkId,
      item: itemCache.value.get(artworkId) ?? null,
    })),
  )

  function cacheItems(items: readonly DiscoveryItem[]) {
    if (items.length === 0) return
    library.seedStatuses(items)
    const next = new Map(itemCache.value)
    items.forEach((item) => next.set(item.artworkId, item))
    itemCache.value = next
  }

  function toggle(item: DiscoveryItem) {
    cacheItems([item])
    if (library.isInLibrary(item.artworkId, item.inLibrary)) return
    const next = new Set(ids.value)
    if (next.has(item.artworkId)) next.delete(item.artworkId)
    else next.add(item.artworkId)
    ids.value = next
  }

  function addAll(candidates: readonly DiscoveryItem[]) {
    cacheItems(candidates)
    addIds(
      candidates
        .filter((item) => !library.isInLibrary(item.artworkId, item.inLibrary))
        .map((item) => item.artworkId),
    )
  }

  function removeAll(candidates: readonly DiscoveryItem[]) {
    removeIds(candidates.map((item) => item.artworkId))
  }

  function addIds(artworkIds: readonly number[]) {
    const availableIds = artworkIds.filter((id) => !library.isInLibrary(id))
    ids.value = new Set([...ids.value, ...availableIds])
    return availableIds
  }

  function removeIds(artworkIds: readonly number[]) {
    const next = new Set(ids.value)
    artworkIds.forEach((artworkId) => next.delete(artworkId))
    ids.value = next
  }

  function setSelected(artworkIds: readonly number[]) {
    ids.value = new Set(artworkIds.filter((id) => !library.isInLibrary(id)))
  }

  function clear() {
    ids.value = new Set()
  }

  watch(
    () => library.statuses,
    () => removeIds(selectedIds.value.filter((id) => library.isInLibrary(id))),
    { flush: 'sync' },
  )

  return {
    selectedIds,
    selectedEntries,
    cacheItems,
    toggle,
    addAll,
    removeAll,
    addIds,
    removeIds,
    setSelected,
    clear,
  }
})
