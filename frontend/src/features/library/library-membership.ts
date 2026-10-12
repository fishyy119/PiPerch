import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface LibraryMembershipSnapshot {
  artworkId: number
  inLibrary: boolean
}

export const useLibraryMembershipStore = defineStore('library-membership', () => {
  const statuses = ref(new Map<number, boolean>())

  function isInLibrary(artworkId: number, fallback = false) {
    return statuses.value.get(artworkId) ?? fallback
  }

  function seedStatuses(items: readonly LibraryMembershipSnapshot[]) {
    const next = new Map(statuses.value)
    // 候选快照仅提供初始状态，不能覆盖后续事件更新的图库状态。
    items.forEach((item) => {
      if (!next.has(item.artworkId)) next.set(item.artworkId, item.inLibrary)
    })
    if (next.size !== statuses.value.size) statuses.value = next
  }

  function applyChange(artworkIds: readonly number[], inLibrary: boolean) {
    const next = new Map(statuses.value)
    artworkIds.forEach((artworkId) => next.set(artworkId, inLibrary))
    statuses.value = next
  }

  return {
    statuses,
    isInLibrary,
    seedStatuses,
    applyChange,
  }
})
