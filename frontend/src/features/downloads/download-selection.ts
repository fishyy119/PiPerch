import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { DiscoveryItem } from './download-api'

export const useDownloadSelection = defineStore('download-selection', () => {
  const ids = ref(new Set<number>())
  const selectedIds = computed(() => [...ids.value])

  function toggle(item: DiscoveryItem) {
    const next = new Set(ids.value)
    if (next.has(item.artworkId)) next.delete(item.artworkId)
    else next.add(item.artworkId)
    ids.value = next
  }

  function addAll(candidates: readonly DiscoveryItem[]) {
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

  return { selectedIds, toggle, addAll, removeAll, addIds, removeIds, clear }
})
