import { createPinia, setActivePinia } from 'pinia'

import { useDownloadSelection } from '@/features/downloads/download-selection'
import { useLibraryMembershipStore } from '@/features/library/library-membership'

import { discoveryItem } from './fixtures'

const first = discoveryItem(100, { title: '第一张图' })
const second = discoveryItem(200, { title: '第二张图' })
const third = discoveryItem(300, { title: '第三张图' })
const fourth = discoveryItem(400, { title: '第四张图' })

describe('下载候选选择', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('跨页添加并按作品 ID 去重', () => {
    const store = useDownloadSelection()
    store.addAll([first])
    store.addAll([first, second])
    store.cacheItems([third])
    store.addIds([200, 300, 400])

    expect(store.selectedIds).toEqual([100, 200, 300, 400])
    expect(store.selectedEntries).toEqual([
      { artworkId: 100, item: first },
      { artworkId: 200, item: second },
      { artworkId: 300, item: third },
      { artworkId: 400, item: null },
    ])

    store.cacheItems([fourth])
    expect(store.selectedEntries[3]).toEqual({ artworkId: 400, item: fourth })
  })

  it('已入库作品移出选择，删除后可重新选择且旧快照不覆盖事件', () => {
    const selection = useDownloadSelection()
    const library = useLibraryMembershipStore()
    selection.addAll([first, second])

    library.applyChange([100], true)
    expect(selection.selectedIds).toEqual([200])

    selection.toggle(first)
    selection.addAll([first])
    selection.addIds([100])
    selection.setSelected([100, 200])
    expect(selection.selectedIds).toEqual([200])

    const oldSnapshot = discoveryItem(100, { inLibrary: true })
    library.applyChange([100], false)
    selection.cacheItems([oldSnapshot])
    expect(selection.selectedIds).toEqual([200])
    selection.toggle(oldSnapshot)
    expect(selection.selectedIds).toEqual([200, 100])

    library.applyChange([300], true)
    expect(selection.addIds([300, 400])).toEqual([400])
    selection.cacheItems([discoveryItem(400, { inLibrary: true })])
    expect(selection.selectedIds).toEqual([200, 100])
  })
})
