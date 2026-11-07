import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useGallerySelectionStore = defineStore('gallery-selection', () => {
  const enabled = ref(false)
  const ids = ref(new Set<number>())
  const selectedIds = computed(() => [...ids.value])
  const selectedCount = computed(() => ids.value.size)

  function isSelected(localArtworkId: number) {
    return ids.value.has(localArtworkId)
  }

  function toggleArtwork(localArtworkId: number) {
    const next = new Set(ids.value)
    if (next.has(localArtworkId)) next.delete(localArtworkId)
    else next.add(localArtworkId)
    ids.value = next
  }

  function clear() {
    ids.value = new Set()
  }

  function setSelected(localArtworkIds: readonly number[]) {
    ids.value = new Set(localArtworkIds)
  }

  function toggleMode() {
    enabled.value = !enabled.value
    if (!enabled.value) clear()
  }

  function toggleVisible(localArtworkIds: readonly number[]) {
    const allSelected =
      localArtworkIds.length > 0 &&
      localArtworkIds.every((localArtworkId) => ids.value.has(localArtworkId))
    const next = new Set(ids.value)
    localArtworkIds.forEach((localArtworkId) => {
      if (allSelected) next.delete(localArtworkId)
      else next.add(localArtworkId)
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
    setSelected,
    toggleMode,
    toggleVisible,
    reset,
  }
})
