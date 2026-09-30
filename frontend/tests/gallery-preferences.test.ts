import {
  clearGalleryPreferences,
  DEFAULT_GALLERY_PREFERENCES,
  GALLERY_PREFERENCES_KEY,
  loadGalleryPreferences,
  saveGalleryPreferences,
} from '@/features/gallery/gallery-preferences'

describe('画廊显示偏好', () => {
  beforeEach(() => localStorage.clear())

  it('保存并读取卡片大小和每页数量', () => {
    saveGalleryPreferences({ cardWidth: 280, pageSize: 48 })

    expect(loadGalleryPreferences()).toEqual({ cardWidth: 280, pageSize: 48 })
  })

  it('无效内容回退到默认设置', () => {
    localStorage.setItem(GALLERY_PREFERENCES_KEY, '{"cardWidth":999,"pageSize":25}')

    expect(loadGalleryPreferences()).toEqual(DEFAULT_GALLERY_PREFERENCES)
  })

  it('重置时仅清除画廊偏好', () => {
    localStorage.setItem(GALLERY_PREFERENCES_KEY, '{}')
    localStorage.setItem('piperch.other.preference', 'keep')

    clearGalleryPreferences()

    expect(localStorage.getItem(GALLERY_PREFERENCES_KEY)).toBeNull()
    expect(localStorage.getItem('piperch.other.preference')).toBe('keep')
  })
})
