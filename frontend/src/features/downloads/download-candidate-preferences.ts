import { defineStore } from 'pinia'
import { ref } from 'vue'
import { z } from 'zod'

export const DOWNLOAD_CANDIDATE_PREFERENCES_KEY = 'piperch.download-candidates.preferences'

const downloadCandidatePreferencesSchema = z.object({
  viewStyle: z.enum(['list', 'artwork']),
  cardWidth: z.number().int().min(140).max(360).multipleOf(10),
})

export type DownloadCandidatePreferences = z.infer<typeof downloadCandidatePreferencesSchema>
export type DownloadCandidateViewStyle = DownloadCandidatePreferences['viewStyle']

export const DEFAULT_DOWNLOAD_CANDIDATE_PREFERENCES: DownloadCandidatePreferences = {
  viewStyle: 'list',
  cardWidth: 220,
}

export function loadDownloadCandidatePreferences(): DownloadCandidatePreferences {
  try {
    const stored = localStorage.getItem(DOWNLOAD_CANDIDATE_PREFERENCES_KEY)
    if (stored === null) return { ...DEFAULT_DOWNLOAD_CANDIDATE_PREFERENCES }
    return downloadCandidatePreferencesSchema.parse(JSON.parse(stored))
  } catch {
    return { ...DEFAULT_DOWNLOAD_CANDIDATE_PREFERENCES }
  }
}

export function saveDownloadCandidatePreferences(preferences: DownloadCandidatePreferences) {
  try {
    localStorage.setItem(DOWNLOAD_CANDIDATE_PREFERENCES_KEY, JSON.stringify(preferences))
  } catch {
    // 浏览器拒绝持久化时仍允许当前页面继续使用偏好。
  }
}

export const useDownloadCandidatePreferences = defineStore('download-candidate-preferences', () => {
  const initialPreferences = loadDownloadCandidatePreferences()
  const viewStyle = ref<DownloadCandidateViewStyle>(initialPreferences.viewStyle)
  const cardWidth = ref(initialPreferences.cardWidth)

  function persist() {
    saveDownloadCandidatePreferences({
      viewStyle: viewStyle.value,
      cardWidth: cardWidth.value,
    })
  }

  function setViewStyle(value: DownloadCandidateViewStyle) {
    viewStyle.value = value
    persist()
  }

  function setCardWidth(value: number) {
    if (!Number.isSafeInteger(value) || value < 140 || value > 360 || value % 10 !== 0) return
    cardWidth.value = value
    persist()
  }

  return { viewStyle, cardWidth, setViewStyle, setCardWidth }
})
