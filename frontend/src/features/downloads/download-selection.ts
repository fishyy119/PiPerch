import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import {
  type ArtworkIdentity,
  artworkReferenceKey,
  type DownloadReference,
} from '@/features/artworks/artwork-source'
import type { DiscoveryItem } from '@/features/discovery/discovery-api'
import { discoveryPreview, type DownloadPreview } from '@/features/downloads/download-preview'
import { useLibraryMembershipStore } from '@/features/library/library-membership'

export type DownloadSelectionEntry = DownloadReference & { preview: DownloadPreview | null }

function downloadReference(item: DiscoveryItem): DownloadReference {
  return item.source === 'fanbox'
    ? { source: item.source, remoteId: item.remoteId, authorId: item.authorId }
    : { source: item.source, remoteId: item.remoteId }
}

export const useDownloadSelection = defineStore('download-selection', () => {
  const library = useLibraryMembershipStore()
  const references = ref(new Map<string, DownloadReference>())
  const candidates = ref(new Map<string, DownloadReference>())
  const previews = ref(new Map<string, DownloadPreview>())
  const selectedReferences = computed(() => [...references.value.values()])
  const selectedEntries = computed<DownloadSelectionEntry[]>(() =>
    selectedReferences.value.map((item) => ({
      ...item,
      preview: previews.value.get(artworkReferenceKey(item.source, item.remoteId)) ?? null,
    })),
  )

  function isSelected(item: ArtworkIdentity) {
    return references.value.has(artworkReferenceKey(item.source, item.remoteId))
  }

  function referenceForKey(key: string) {
    return references.value.get(key) ?? candidates.value.get(key)
  }

  function cachePreviews(items: readonly DownloadPreview[]) {
    const next = new Map(previews.value)
    for (const item of items) next.set(artworkReferenceKey(item.source, item.remoteId), item)
    previews.value = next
  }

  function cacheItems(items: readonly DiscoveryItem[]) {
    if (items.length === 0) return
    library.seedStatuses(items)
    const next = new Map(candidates.value)
    for (const item of items)
      next.set(artworkReferenceKey(item.source, item.remoteId), downloadReference(item))
    candidates.value = next
    cachePreviews(items.map(discoveryPreview))
  }

  function add(items: readonly DownloadReference[]) {
    const available = items.filter(
      (item) => !library.isInLibrary(item.remoteId, false, item.source),
    )
    const next = new Map(references.value)
    for (const item of available) next.set(artworkReferenceKey(item.source, item.remoteId), item)
    references.value = next
    return available
  }

  function remove(items: readonly ArtworkIdentity[]) {
    const next = new Map(references.value)
    for (const item of items) next.delete(artworkReferenceKey(item.source, item.remoteId))
    references.value = next
  }

  function toggle(item: DiscoveryItem) {
    cacheItems([item])
    if (library.isInLibrary(item.remoteId, item.inLibrary, item.source)) return
    if (isSelected(item)) remove([item])
    else add([downloadReference(item)])
  }

  function addAll(items: readonly DiscoveryItem[]) {
    cacheItems(items)
    add(items.map(downloadReference))
  }

  function removeAll(items: readonly DiscoveryItem[]) {
    remove(items)
  }

  function setSelected(items: readonly DownloadReference[]) {
    references.value = new Map(
      items
        .filter((item) => !library.isInLibrary(item.remoteId, false, item.source))
        .map((item) => [artworkReferenceKey(item.source, item.remoteId), item]),
    )
  }

  function clear() {
    references.value = new Map()
  }

  watch(
    () => library.statuses,
    () =>
      remove(
        selectedReferences.value.filter((item) =>
          library.isInLibrary(item.remoteId, false, item.source),
        ),
      ),
    { flush: 'sync' },
  )

  return {
    selectedReferences,
    selectedEntries,
    isSelected,
    referenceForKey,
    cacheItems,
    cachePreviews,
    toggle,
    addAll,
    removeAll,
    add,
    remove,
    setSelected,
    clear,
  }
})
