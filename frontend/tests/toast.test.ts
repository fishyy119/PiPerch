import { render, screen } from '@testing-library/vue'
import { nextTick } from 'vue'

import { toast } from '@ui/toast'
import ToastHost from '@ui/ToastHost.vue'

describe('Toast 通知', () => {
  afterEach(() => {
    toast.dismiss()
    vi.useRealTimers()
  })

  it('通过共享出口显示带状态的通知', async () => {
    render(ToastHost)

    toast.success('设置已保存')

    const notification = await screen.findByText('设置已保存')
    expect(notification.closest('[data-sonner-toast]')).toHaveAttribute('data-type', 'success')
  })

  it('在持续时间结束后自动关闭', async () => {
    vi.useFakeTimers()
    render(ToastHost)

    toast.success('短暂通知', { duration: 100 })
    await nextTick()
    await nextTick()
    expect(screen.getByText('短暂通知')).toBeInTheDocument()

    await vi.advanceTimersByTimeAsync(500)
    await nextTick()
    expect(screen.queryByText('短暂通知')).not.toBeInTheDocument()
  })
})
