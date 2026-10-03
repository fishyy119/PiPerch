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
    await user.click(localCheckbox)
    expect(onToggle).not.toHaveBeenCalled()

    await user.click(remoteCheckbox)
    expect(onToggle).toHaveBeenCalledWith(selectable)
  })
})
