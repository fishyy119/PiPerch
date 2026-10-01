import { createPinia, setActivePinia } from 'pinia'

import type { DiscoveryItem } from '@/features/downloads/download-api'
import { useDownloadSelection } from '@/features/downloads/download-selection'

const first: DiscoveryItem = {
  artworkId: 100,
  title: '第一张图',
  authorName: '作者',
  artworkType: 'illust',
  pageCount: 1,
  xRestrict: 0,
  isAi: false,
  thumbnailUrl: null,
  inLibrary: false,
}

const second: DiscoveryItem = { ...first, artworkId: 200, title: '第二张图' }
const third: DiscoveryItem = { ...first, artworkId: 300, title: '第三张图' }
const fourth: DiscoveryItem = { ...first, artworkId: 400, title: '第四张图' }

describe('下载候选选择', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('跨页添加并按作品 ID 去重', () => {
    const store = useDownloadSelection()
    store.addAll([first])
    store.addAll([first, second])
    store.remember([third])
    store.addIds([200, 300, 400])

    expect(store.selectedIds).toEqual([100, 200, 300, 400])
    expect(store.selectedEntries).toEqual([
      { artworkId: 100, item: first },
      { artworkId: 200, item: second },
      { artworkId: 300, item: third },
      { artworkId: 400, item: null },
    ])

    store.remember([fourth])
    expect(store.selectedEntries[3]).toEqual({ artworkId: 400, item: fourth })
  })

  it('支持单项切换、本页移除和清空', () => {
    const store = useDownloadSelection()
    store.toggle(first)
    store.toggle(second)
    store.removeAll([first])
    expect(store.selectedIds).toEqual([200])

    store.addIds([300, 400])
    store.removeIds([200, 400])
    expect(store.selectedIds).toEqual([300])

    store.clear()
    expect(store.selectedIds).toEqual([])
    expect(store.selectedEntries).toEqual([])

    store.addIds([100])
    expect(store.selectedEntries).toEqual([{ artworkId: 100, item: first }])
  })
})
