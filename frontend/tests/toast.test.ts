import { render, screen } from '@testing-library/vue'

import { toast } from '@ui/toast'
import ToastHost from '@ui/ToastHost.vue'

describe('Toast 通知', () => {
  afterEach(() => toast.dismiss())

  it('通过共享出口显示带状态的通知', async () => {
    render(ToastHost)

    toast.success('设置已保存')

    const notification = await screen.findByText('设置已保存')
    expect(notification.closest('[data-sonner-toast]')).toHaveAttribute('data-type', 'success')
  })
})
