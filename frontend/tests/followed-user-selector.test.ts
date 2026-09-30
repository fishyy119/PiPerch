import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { vi } from 'vitest'

import type { FollowedUser } from '@/features/downloads/download-api'
import FollowedUserSelector from '@/pages/downloads/FollowedUserSelector.vue'

const users: FollowedUser[] = [
  {
    userId: 101,
    name: '第一位作者',
    avatarUrl: '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2F101.jpg',
  },
  { userId: 102, name: '第二位作者', avatarUrl: null },
]

describe('已关注作者选择', () => {
  it('显示头像、当前高亮状态并发送作者选择', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    const { container } = render(FollowedUserSelector, {
      props: { users, selectedUserId: 101, onSelect },
    })

    expect(screen.getByRole('button', { name: '第一位作者' })).toHaveClass('border-primary')
    expect(container.querySelector('img')).toHaveAttribute(
      'src',
      '/api/pixiv-images?url=https%3A%2F%2Fi.pximg.net%2F101.jpg',
    )

    await user.click(screen.getByRole('button', { name: '第二位作者' }))
    expect(onSelect).toHaveBeenCalledWith(users[1])
  })
})
