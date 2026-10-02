import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { vi } from 'vitest'

import DiscoveryCandidateResults from '@/pages/downloads/DiscoveryCandidateResults.vue'

import { discoveryItem } from './fixtures'

const candidate = discoveryItem(123, {
  title: '测试作品',
  thumbnailUrl: '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2Fexample.jpg',
  inLibrary: true,
})

describe('候选作品显示', () => {
  it('仅允许勾选尚未入库的候选作品', async () => {
    const user = userEvent.setup()
    const selectable = { ...candidate, artworkId: 456, inLibrary: false }
    const onToggle = vi.fn()
    render(DiscoveryCandidateResults, {
      props: { candidates: [candidate, selectable], selectedIds: [], onToggle },
    })

    const [localCheckbox, remoteCheckbox] = screen.getAllByRole('checkbox')
    if (!localCheckbox || !remoteCheckbox) throw new Error('缺少候选作品复选框。')
    expect(localCheckbox).toBeDisabled()
    await user.click(localCheckbox)
    expect(onToggle).not.toHaveBeenCalled()

    await user.click(remoteCheckbox)
    expect(onToggle).toHaveBeenCalledWith(selectable)
  })

  it('作品视图仅允许将尚未入库的作品加入队列', async () => {
    const user = userEvent.setup()
    const selectable = { ...candidate, artworkId: 456, inLibrary: false }
    const onToggle = vi.fn()
    render(DiscoveryCandidateResults, {
      props: {
        candidates: [candidate, selectable],
        selectedIds: [],
        viewStyle: 'artwork',
        onToggle,
      },
      global: {
        plugins: [[VueQueryPlugin, { queryClient: new QueryClient() }]],
      },
    })

    expect(screen.getByText('已在图库')).toBeInTheDocument()
    const queueButtons = screen.getAllByTitle('加入待提交队列')
    expect(queueButtons).toHaveLength(1)
    const queueButton = queueButtons[0]
    if (!queueButton) throw new Error('缺少加入待提交队列按钮。')
    await user.click(queueButton)
    expect(onToggle).toHaveBeenCalledWith(selectable)
  })
})
