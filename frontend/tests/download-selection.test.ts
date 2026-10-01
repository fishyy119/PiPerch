import { createPinia, setActivePinia } from 'pinia'

import { useDownloadSelection } from '@/features/downloads/download-selection'

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
