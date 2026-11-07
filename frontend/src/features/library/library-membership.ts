import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  artworkReferenceKey,
  type ArtworkSource,
  type LibraryArtworkReference,
} from '@/features/artworks/artwork-source'

export interface LibraryMembershipSnapshot {
  remoteId: number
  inLibrary: boolean
  source: ArtworkSource
  localArtworkId: number | null
}

export const useLibraryMembershipStore = defineStore('library-membership', () => {
  const statuses = ref(new Map<string, boolean>())
  const localIds = ref(new Map<string, number>())

  function isInLibrary(artworkId: number, fallback = false, source: ArtworkSource = 'pixiv') {
    return statuses.value.get(artworkReferenceKey(source, artworkId)) ?? fallback
  }

  function localId(
    remoteId: number,
    source: ArtworkSource = 'pixiv',
    fallback: number | null = null,
  ) {
    return localIds.value.get(artworkReferenceKey(source, remoteId)) ?? fallback
  }

  function seedStatuses(items: readonly LibraryMembershipSnapshot[]) {
    const next = new Map(statuses.value)
    // 候选快照仅提供初始状态，不能覆盖后续事件更新的图库状态。
    items.forEach((item) => {
      const key = artworkReferenceKey(item.source, item.remoteId)
      if (!next.has(key)) next.set(key, item.inLibrary)
      if (item.localArtworkId != null && !localIds.value.has(key))
        localIds.value.set(key, item.localArtworkId)
    })
    if (next.size !== statuses.value.size) statuses.value = next
  }

  function applyChange(
    artworkIds: readonly number[],
    inLibrary: boolean,
    source: ArtworkSource = 'pixiv',
  ) {
    const next = new Map(statuses.value)
    artworkIds.forEach((artworkId) => next.set(artworkReferenceKey(source, artworkId), inLibrary))
    statuses.value = next
  }

  function applyReference(item: LibraryArtworkReference, inLibrary: boolean) {
    localIds.value.set(artworkReferenceKey(item.source, item.remoteId), item.localArtworkId)
    applyChange([item.remoteId], inLibrary, item.source)
  }

  return {
    statuses,
    localId,
    isInLibrary,
    seedStatuses,
    applyReference,
  }
})
