import type { Ref } from 'vue'

import { artworkReferenceKey } from '@/features/artworks/artwork-source'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useMarqueeSelection } from '@/shared/lib/useMarqueeSelection'

export function useDownloadMarqueeSelection(root: Ref<HTMLElement | null>) {
  const selection = useDownloadSelection()
  return useMarqueeSelection(root, {
    selectedItems: () => selection.selectedReferences,
    setSelectedItems: selection.setSelected,
    getKey: (item) => artworkReferenceKey(item.source, item.remoteId),
    resolveItem: (element) => selection.referenceForKey(element.dataset.selectionId ?? ''),
    canStart: (event) =>
      !event.ctrlKey || !(event.target instanceof Element) || !event.target.closest('a'),
  })
}
