import type { Get, Paths } from 'type-fest'

export interface PreferenceConfig {
  gallery: {
    cardWidth: number
    pageSize: number
    showTitle: boolean
    showAuthor: boolean
    showFavoriteIndicator: boolean
  }
  discovery: {
    cardWidth: number
    authorColumns: number
  }
  artworkDetail: {
    relatedCardWidth: number
    relatedCount: number
  }
  downloadCandidates: {
    cardWidth: number
  }
}

export const PREFERENCE_DEFAULTS: PreferenceConfig = {
  gallery: {
    cardWidth: 220,
    pageSize: 24,
    showTitle: true,
    showAuthor: true,
    showFavoriteIndicator: true,
  },
  discovery: {
    cardWidth: 220,
    authorColumns: 1,
  },
  artworkDetail: {
    relatedCardWidth: 160,
    relatedCount: 12,
  },
  downloadCandidates: {
    cardWidth: 220,
  },
}

export type PreferenceKey = Extract<Paths<PreferenceConfig, { leavesOnly: true }>, string>
export type PreferenceValue<Key extends PreferenceKey> = Get<PreferenceConfig, Key>

const STORAGE_PREFIX = 'piperch.preferences.'

function defaultValue<Key extends PreferenceKey>(key: Key): PreferenceValue<Key> {
  return key
    .split('.')
    .reduce<unknown>(
      (value, name) => (value as Record<string, unknown>)[name],
      PREFERENCE_DEFAULTS,
    ) as PreferenceValue<Key>
}

function storageKey(key: PreferenceKey) {
  return `${STORAGE_PREFIX}${key}`
}

function parseStoredValue<Key extends PreferenceKey>(
  stored: string,
  fallback: PreferenceValue<Key>,
): PreferenceValue<Key> {
  if (typeof fallback === 'number') {
    return Number(stored) as PreferenceValue<Key>
  }
  if (typeof fallback === 'boolean') {
    return (stored === 'true') as PreferenceValue<Key>
  }
  return stored as PreferenceValue<Key>
}

export function setPreference<Key extends PreferenceKey>(key: Key, value: PreferenceValue<Key>) {
  try {
    localStorage.setItem(storageKey(key), String(value))
  } catch {
    // 浏览器拒绝持久化时仍允许当前页面继续使用偏好。
  }
}

export function getPreference<Key extends PreferenceKey>(key: Key): PreferenceValue<Key> {
  const fallback = defaultValue(key)
  try {
    const stored = localStorage.getItem(storageKey(key))
    return stored === null ? fallback : parseStoredValue(stored, fallback)
  } catch {
    return fallback
  }
}
