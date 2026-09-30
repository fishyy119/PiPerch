import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import FilterButton from '@ui/FilterButton.vue'

describe('图库筛选按钮', () => {
  it('仅有规则时显示数量和清除按钮，清除操作不会打开筛选', async () => {
    const user = userEvent.setup()
    const rendered = render(FilterButton, {
      props: { activeCount: 3 },
    })

    expect(screen.getByText('3')).toBeInTheDocument()

    const [, clearButton] = screen.getAllByRole('button')
    if (clearButton === undefined) throw new Error('缺少快速清除按钮。')
    await user.click(clearButton)

    expect(rendered.emitted().clear).toHaveLength(1)
    expect(rendered.emitted().toggle).toBeUndefined()
    await rendered.rerender({ activeCount: 0 })
    expect(screen.queryByText('3')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })
})
