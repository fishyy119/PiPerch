import { createPinia, setActivePinia } from 'pinia'

import type { DownloadReference } from '@/features/artworks/artwork-source'
import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useLibraryMembershipStore } from '@/features/library/library-membership'

import { discoveryItem } from './fixtures'

function pixivReferences(...ids: number[]): DownloadReference[] {
  return ids.map((remoteId) => ({ source: 'pixiv', remoteId }))
}

describe('下载候选选择', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('跨页选择保留同号不同来源的作品，并按完整身份去重', () => {
    const selection = useDownloadSelection()
    const first = discoveryItem(100)
    const second = discoveryItem(200)
    const fanbox = discoveryItem(100, { source: 'fanbox', authorId: 42 })
    selection.addAll([first, second])
    selection.addAll([first, fanbox])
    selection.setSelected([
      ...selection.selectedReferences,
      { source: 'fanbox', remoteId: 100, authorId: 42 },
    ])

    expect(selection.selectedReferences).toEqual([
      ...pixivReferences(100, 200),
      { source: 'fanbox', remoteId: 100, authorId: 42 },
    ])
  })

  it('已入库作品不可重选，旧快照和预览不能覆盖馆藏事件', () => {
    const selection = useDownloadSelection()
    const library = useLibraryMembershipStore()
    const first = discoveryItem(100)
    selection.addAll([first, discoveryItem(200)])
    library.applyReference({ source: 'pixiv', remoteId: 100, localArtworkId: 501 }, true)
    selection.toggle(first)
    selection.setSelected(pixivReferences(100, 200))
    expect(selection.selectedReferences).toEqual(pixivReferences(200))

    library.applyReference({ source: 'pixiv', remoteId: 100, localArtworkId: 501 }, false)
    const oldSnapshot = discoveryItem(100, { inLibrary: true, localArtworkId: 1 })
    selection.cacheItems([oldSnapshot])
    selection.toggle(oldSnapshot)
    expect(selection.selectedReferences).toEqual(pixivReferences(200, 100))
    expect(library.localId(100)).toBe(501)

    library.applyReference({ source: 'pixiv', remoteId: 300, localArtworkId: 300 }, true)
    expect(selection.add(pixivReferences(300, 400))).toEqual(pixivReferences(400))
    selection.cacheItems([discoveryItem(400, { inLibrary: true })])
    expect(selection.selectedReferences).toEqual(pixivReferences(200, 100))

    selection.cachePreviews([{ source: 'fanbox', remoteId: 900, thumbnailUrl: null }])
    selection.cacheItems([
      discoveryItem(900, {
        source: 'fanbox',
        authorId: 42,
        inLibrary: true,
        localArtworkId: 1234,
      }),
    ])
    expect(library.isInLibrary(900, false, 'fanbox')).toBe(true)

    selection.clear()
    selection.add([...pixivReferences(100), { source: 'fanbox', remoteId: 100, authorId: 42 }])
    library.applyReference({ source: 'pixiv', remoteId: 100, localArtworkId: 502 }, true)
    expect(selection.selectedReferences).toEqual([
      { source: 'fanbox', remoteId: 100, authorId: 42 },
    ])
  })
})
