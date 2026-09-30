import { z } from 'zod'

export const GALLERY_PREFERENCES_KEY = 'piperch.gallery.preferences'
export const GALLERY_PAGE_SIZE_OPTIONS = [24, 48, 96] as const

const galleryPreferencesSchema = z.object({
  cardWidth: z.number().int().min(140).max(360).multipleOf(10),
  pageSize: z.union([z.literal(24), z.literal(48), z.literal(96)]),
})

export type GalleryPreferences = z.infer<typeof galleryPreferencesSchema>

export const DEFAULT_GALLERY_PREFERENCES: GalleryPreferences = {
  cardWidth: 220,
  pageSize: 24,
}

export function loadGalleryPreferences(): GalleryPreferences {
  try {
    const stored = localStorage.getItem(GALLERY_PREFERENCES_KEY)
    if (stored === null) return { ...DEFAULT_GALLERY_PREFERENCES }
    return galleryPreferencesSchema.parse(JSON.parse(stored))
  } catch {
    return { ...DEFAULT_GALLERY_PREFERENCES }
  }
}

export function saveGalleryPreferences(preferences: GalleryPreferences) {
  try {
    localStorage.setItem(GALLERY_PREFERENCES_KEY, JSON.stringify(preferences))
  } catch {
    // 浏览器拒绝持久化时仍允许当前页面继续使用偏好。
  }
}

export function clearGalleryPreferences() {
  try {
    localStorage.removeItem(GALLERY_PREFERENCES_KEY)
  } catch {
    // 清除失败不应阻断画廊操作。
  }
}
