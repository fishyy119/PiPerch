import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { vi } from 'vitest'

import type { BookmarkFolder } from '@/features/discovery/discovery-api'
import BookmarkFolderSelector from '@/pages/downloads/BookmarkFolderSelector.vue'

const folders: BookmarkFolder[] = [
  { visibility: 'public', tag: null, kind: 'all', name: '全部收藏', itemCount: 10 },
  {
    visibility: 'public',
    tag: '未分類',
    kind: 'uncategorized',
    name: '未分类',
    itemCount: 2,
  },
  { visibility: 'public', tag: '风景', kind: 'tag', name: '风景', itemCount: 5 },
  { visibility: 'private', tag: null, kind: 'all', name: '全部收藏', itemCount: 4 },
  { visibility: 'private', tag: '风景', kind: 'tag', name: '风景', itemCount: 3 },
]

describe('收藏夹选择', () => {
  it('同一范围内让全部收藏与普通标签互斥', async () => {
    const user = userEvent.setup()
    const onUpdate = vi.fn()
    const view = render(BookmarkFolderSelector, {
      props: {
        folders,
        selectedFolders: [
          { visibility: 'public', tag: '风景' },
          { visibility: 'private', tag: '风景' },
        ],
        'onUpdate:selectedFolders': onUpdate,
      },
    })

    const [publicAll] = screen.getAllByRole('button', { name: /全部收藏/u })
    if (!publicAll) throw new Error('缺少公开全部收藏选项。')
    await user.click(publicAll)
    expect(onUpdate).toHaveBeenLastCalledWith([
      { visibility: 'public', tag: null },
      { visibility: 'private', tag: '风景' },
    ])

    await view.rerender({
      folders,
      selectedFolders: [
        { visibility: 'public', tag: null },
        { visibility: 'private', tag: '风景' },
      ],
      'onUpdate:selectedFolders': onUpdate,
    })
    const [publicLandscape] = screen.getAllByRole('button', { name: /风景/u })
    if (!publicLandscape) throw new Error('缺少公开风景收藏夹。')
    await user.click(publicLandscape)
    expect(onUpdate).toHaveBeenLastCalledWith([
      { visibility: 'public', tag: '风景' },
      { visibility: 'private', tag: '风景' },
    ])
  })
})
