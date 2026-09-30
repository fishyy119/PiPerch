import { z } from 'zod'

import { api } from '@/shared/api/http'

export const settingsSchema = z.object({
  pixivCookie: z.string().nullable(),
  proxyUrl: z.string().nullable(),
  libraryRoot: z.string(),
  downloadConcurrency: z.number().int().min(1).max(8),
  requestIntervalMs: z.number().int().min(0).max(60_000),
})
export type Settings = z.infer<typeof settingsSchema>

const cookieValidationSchema = z.object({ valid: z.boolean() })

export async function getSettings() {
  return settingsSchema.parse(await api.get<unknown>('/api/settings'))
}

export async function updateSettings(settings: Settings) {
  return settingsSchema.parse(await api.put<unknown>('/api/settings', settings))
}

export async function validatePixivCookie(value: string) {
  return cookieValidationSchema.parse(
    await api.post<unknown>('/api/settings/pixiv-cookie/validate', { value }),
  )
}
