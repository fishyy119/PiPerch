import type { Ref } from 'vue'

import { useMarqueeSelection } from '@/shared/lib/useMarqueeSelection'

import { artworkReferenceKey } from '../artworks/artwork-source'
import { useDownloadSelection } from './download-selection'

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
