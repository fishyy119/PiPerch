import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import ConfirmDialog from '@ui/ConfirmDialog.vue'
import Dialog from '@ui/Dialog.vue'

describe('弹层组件', () => {
  it('允许通过 Escape 请求关闭普通弹层', async () => {
    const user = userEvent.setup()
    const rendered = render(Dialog, {
      props: { open: true, title: '筛选本地作品' },
      slots: { default: '<p>筛选内容</p>' },
    })

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    await user.keyboard('{Escape}')

    expect(rendered.emitted()['update:open']).toEqual([[false]])
  })

  it('确认操作保持弹层打开，取消操作请求关闭', async () => {
    const user = userEvent.setup()
    const rendered = render(ConfirmDialog, {
      props: {
        open: true,
        title: '永久删除作品',
        description: '此操作无法撤销。',
        confirmText: '永久删除',
      },
    })

    await user.click(await screen.findByRole('button', { name: '永久删除' }))
    expect(rendered.emitted().confirm).toHaveLength(1)
    expect(rendered.emitted().close).toBeUndefined()

    await user.click(screen.getByRole('button', { name: '取消' }))
    expect(rendered.emitted().close).toHaveLength(1)
  })
})
