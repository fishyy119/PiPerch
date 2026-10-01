import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import NumberInput from '@ui/NumberInput.vue'

describe('NumberInput', () => {
  it('失焦时提交范围内的数字', async () => {
    const user = userEvent.setup()
    const view = render(NumberInput, {
      props: { modelValue: 3, min: 1, max: 8 },
    })

    const input = screen.getByRole('spinbutton')
    await user.clear(input)
    await user.type(input, '6')
    await user.tab()

    expect(view.emitted('update:modelValue')).toEqual([[6]])
    expect(view.emitted('commit')).toEqual([[6]])
    expect(input).toHaveValue(6)
  })

  it('失焦时恢复空值和越界值', async () => {
    const user = userEvent.setup()
    const view = render(NumberInput, {
      props: { modelValue: 3, min: 1, max: 8 },
    })

    const input = screen.getByRole('spinbutton')
    await user.clear(input)
    await user.tab()
    expect(input).toHaveValue(3)

    await user.clear(input)
    await user.type(input, '9')
    await user.tab()
    expect(input).toHaveValue(3)
    expect(view.emitted('update:modelValue')).toBeUndefined()
    expect(view.emitted('commit')).toBeUndefined()
  })
})
