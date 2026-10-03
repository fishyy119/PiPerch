import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useGallerySelectionStore = defineStore('gallery-selection', () => {
  const enabled = ref(false)
  const ids = ref(new Set<number>())
  const selectedIds = computed(() => [...ids.value])
  const selectedCount = computed(() => ids.value.size)

  function isSelected(artworkId: number) {
    return ids.value.has(artworkId)
  }

  function toggleArtwork(artworkId: number) {
    const next = new Set(ids.value)
    if (next.has(artworkId)) next.delete(artworkId)
    else next.add(artworkId)
    ids.value = next
  }

  function clear() {
    ids.value = new Set()
  }

  function toggleMode() {
    enabled.value = !enabled.value
    if (!enabled.value) clear()
  }

  function toggleVisible(artworkIds: readonly number[]) {
    const allSelected =
      artworkIds.length > 0 && artworkIds.every((artworkId) => ids.value.has(artworkId))
    const next = new Set(ids.value)
    artworkIds.forEach((artworkId) => {
      if (allSelected) next.delete(artworkId)
      else next.add(artworkId)
    })
    ids.value = next
  }

  function reset() {
    enabled.value = false
    clear()
  }

  return {
    enabled,
    selectedIds,
    selectedCount,
    isSelected,
    toggleArtwork,
    clear,
    toggleMode,
    toggleVisible,
    reset,
  }
})
