import { z } from 'zod'

const DISCOVERY_PREFERENCES_KEY = 'piperch.discovery.preferences'
export const DISCOVERY_AUTHOR_COLUMN_OPTIONS = [1, 2, 3] as const

const discoveryPreferencesSchema = z.object({
  cardWidth: z.number().int().min(140).max(360).multipleOf(10),
  authorColumns: z.union([z.literal(1), z.literal(2), z.literal(3)]).default(1),
})

type DiscoveryPreferences = z.infer<typeof discoveryPreferencesSchema>

const DEFAULT_DISCOVERY_PREFERENCES: DiscoveryPreferences = {
  cardWidth: 220,
  authorColumns: 1,
}

export function loadDiscoveryPreferences(): DiscoveryPreferences {
  try {
    const stored = localStorage.getItem(DISCOVERY_PREFERENCES_KEY)
    if (stored === null) return { ...DEFAULT_DISCOVERY_PREFERENCES }
    return discoveryPreferencesSchema.parse(JSON.parse(stored))
  } catch {
    return { ...DEFAULT_DISCOVERY_PREFERENCES }
  }
}

export function saveDiscoveryPreferences(preferences: DiscoveryPreferences) {
  try {
    localStorage.setItem(DISCOVERY_PREFERENCES_KEY, JSON.stringify(preferences))
  } catch {
    // 浏览器拒绝持久化时仍允许当前页面继续使用偏好。
  }
}
