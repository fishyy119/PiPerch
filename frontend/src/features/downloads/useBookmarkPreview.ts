import { onScopeDispose, ref } from 'vue'

import {
  type BookmarkFolderReference,
  discover,
  type DiscoveryItem,
} from '@/features/discovery/discovery-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'

interface BookmarkStreamProgress {
  folder: BookmarkFolderReference
  nextPage: number | null
}

const BOOKMARK_PAGE_SIZE = 48

export function useBookmarkPreview() {
  const selection = useDownloadSelection()
  const candidates = ref<DiscoveryItem[]>([])
  const cachedCandidates = ref<DiscoveryItem[]>([])
  const seenIds = ref(new Set<number>())
  const streams = ref<BookmarkStreamProgress[]>([])
  const streamCursor = ref(0)
  const previewVersion = ref(0)
  const page = ref(0)
  const nextPage = ref<number | null>(null)

  function reset(folders: readonly BookmarkFolderReference[]) {
    previewVersion.value += 1
    candidates.value = []
    cachedCandidates.value = []
    seenIds.value = new Set()
    streams.value = folders.map((folder) => ({
      folder: { visibility: folder.visibility, tag: folder.tag },
      nextPage: 0,
    }))
    streamCursor.value = 0
    page.value = 0
    nextPage.value = null
  }

  function hasPendingStreams() {
    return streams.value.some((stream) => stream.nextPage !== null)
  }

  function nextStreamIndex() {
    const streamCount = streams.value.length
    for (let offset = 0; offset < streamCount; offset += 1) {
      const index = (streamCursor.value + offset) % streamCount
      const stream = streams.value[index]
      if (stream !== undefined && stream.nextPage !== null) return index
    }
    return null
  }

  async function loadPage(targetPage: number) {
    const currentPreviewVersion = previewVersion.value
    const requiredCount = (targetPage + 1) * BOOKMARK_PAGE_SIZE
    while (cachedCandidates.value.length < requiredCount) {
      const streamIndex = nextStreamIndex()
      if (streamIndex === null) break
      const stream = streams.value[streamIndex]
      if (stream === undefined) throw new Error('收藏分页状态无效。')
      if (stream.nextPage === null) break
      const result = await discover({
        sourceType: 'bookmark',
        folder: stream.folder,
        page: stream.nextPage,
      })
      if (currentPreviewVersion !== previewVersion.value) return
      stream.nextPage = result.nextPage
      streamCursor.value = (streamIndex + 1) % streams.value.length
      selection.remember(result.items)
      selection.removeAll(result.items.filter((item) => item.inLibrary))

      const nextSeenIds = new Set(seenIds.value)
      const uniqueItems = result.items.filter((item) => {
        if (nextSeenIds.has(item.artworkId)) return false
        nextSeenIds.add(item.artworkId)
        return true
      })
      seenIds.value = nextSeenIds
      cachedCandidates.value = [...cachedCandidates.value, ...uniqueItems]
    }

    const start = targetPage * BOOKMARK_PAGE_SIZE
    const pageItems = cachedCandidates.value.slice(start, start + BOOKMARK_PAGE_SIZE)
    if (targetPage > 0 && pageItems.length === 0) {
      nextPage.value = null
      return
    }
    candidates.value = pageItems
    page.value = targetPage
    nextPage.value =
      cachedCandidates.value.length > start + BOOKMARK_PAGE_SIZE || hasPendingStreams()
        ? targetPage + 1
        : null
  }

  onScopeDispose(() => {
    previewVersion.value += 1
  })

  return { candidates, page, nextPage, reset, loadPage }
}
