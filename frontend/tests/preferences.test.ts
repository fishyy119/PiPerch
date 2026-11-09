import { getPreference, PREFERENCE_DEFAULTS, setPreference } from '@/app/preferences'
import { usePreference } from '@/app/usePreference'

describe('本地偏好存储', () => {
  beforeEach(() => localStorage.clear())

  it('按叶子组合键保存偏好，并在值缺失时读取默认值', () => {
    expect(getPreference('gallery.cardWidth')).toBe(PREFERENCE_DEFAULTS.gallery.cardWidth)
    expect(localStorage.getItem('piperch.preferences.gallery.cardWidth')).toBeNull()

    setPreference('gallery.cardWidth', 225)
    setPreference('gallery.masonryImageWidth', 310)

    expect(getPreference('gallery.cardWidth')).toBe(225)
    expect(getPreference('gallery.masonryImageWidth')).toBe(310)
    expect(localStorage.getItem('piperch.preferences.gallery.cardWidth')).toBe('225')
    expect(localStorage.getItem('piperch.preferences.gallery.masonryImageWidth')).toBe('310')
  })

  it('同一偏好键在不同调用方之间共享响应式状态', () => {
    const first = usePreference('discovery.authorColumns')
    const second = usePreference('discovery.authorColumns')

    first.value = 3

    expect(second.value).toBe(3)
    expect(localStorage.getItem('piperch.preferences.discovery.authorColumns')).toBe('3')
  })
})
