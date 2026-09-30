import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'

import type { ArtworkSummary } from '@/features/gallery/gallery-api'
import ArtworkGridItem from '@/pages/gallery/ArtworkGridItem.vue'

const artwork: ArtworkSummary = {
  artworkId: 123,
  title: '多页测试作品',
  artworkType: 'manga',
  authorId: 456,
  authorName: '测试作者',
  seriesId: null,
  seriesTitle: null,
  pageCount: 3,
  xRestrict: 0,
  isAi: false,
  publishedAt: null,
  downloadedAt: '2026-09-28T00:00:00Z',
}

describe('图库作品卡片', () => {
  it('按作品页数显示快速预览点并延迟加载原图', async () => {
    const user = userEvent.setup()
    render(ArtworkGridItem, {
      props: { artwork, selected: false, selectionMode: false },
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    const previewDots = screen.getAllByRole('button').filter((button) => button.textContent === '')
    expect(previewDots).toHaveLength(3)
    expect(screen.queryByAltText('多页测试作品 第 2 页快速预览')).not.toBeInTheDocument()
    const [, secondPreviewDot] = previewDots
    if (secondPreviewDot === undefined) throw new Error('缺少第二页快速预览按钮。')

    await user.hover(secondPreviewDot)

    const previewImage = await screen.findByAltText('多页测试作品 第 2 页快速预览')
    expect(previewImage).toHaveAttribute('src', '/api/artworks/123/pages/1')
    expect(previewImage).toBeVisible()

    const thirdPreviewDot = previewDots[2]
    if (thirdPreviewDot === undefined) throw new Error('缺少第三页快速预览按钮。')
    await user.hover(thirdPreviewDot)

    expect(screen.queryByAltText('多页测试作品 第 2 页快速预览')).not.toBeInTheDocument()
    expect(await screen.findByAltText('多页测试作品 第 3 页快速预览')).toHaveAttribute(
      'src',
      '/api/artworks/123/pages/2',
    )
    expect(document.body.querySelectorAll('[data-app-hover-card-content]')).toHaveLength(1)

    await user.unhover(thirdPreviewDot)
    await fireEvent.pointerMove(document.body, { clientX: 100, clientY: 100 })
    await waitFor(() => {
      expect(screen.queryByAltText('多页测试作品 第 3 页快速预览')).not.toBeInTheDocument()
    })
  })
})
