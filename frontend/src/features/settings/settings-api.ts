import { z } from 'zod'

import { api } from '@/shared/api/http'

export const settingsSchema = z.object({
  pixivCookie: z.string().nullable(),
  proxyUrl: z.string().nullable(),
  libraryRoot: z.string(),
  downloadConcurrency: z.number().int().min(1).max(8),
  requestIntervalMs: z.number().int().min(0).max(60_000),
  webpEnabled: z.boolean(),
  webpQuality: z.number().int().min(1).max(100),
})
export type Settings = z.infer<typeof settingsSchema>
export type SettingsPatch = Partial<Omit<Settings, 'libraryRoot'>>

const cookieValidationSchema = z.object({ valid: z.boolean() })
const libraryMigrationSchema = z.discriminatedUnion('status', [
  z.object({ status: z.literal('cancelled'), message: z.string() }),
  z.object({
    status: z.literal('started'),
    message: z.string(),
    targetPath: z.string(),
    instanceId: z.string(),
  }),
])
const healthSchema = z.object({
  status: z.literal('ok'),
  database: z.literal('ok'),
  instanceId: z.string(),
})

export async function getSettings() {
  return settingsSchema.parse(await api.get<unknown>('/api/settings'))
}

export async function patchSettings(settings: SettingsPatch) {
  return settingsSchema.parse(await api.patch<unknown>('/api/settings', settings))
}

export async function validatePixivCookie(value: string) {
  return cookieValidationSchema.parse(
    await api.post<unknown>('/api/settings/pixiv-cookie/validate', { value }),
  )
}

export async function migrateLibraryRoot() {
  return libraryMigrationSchema.parse(await api.post<unknown>('/api/settings/library-root/migrate'))
}

export async function getHealth() {
  return healthSchema.parse(await api.get<unknown>('/api/health'))
}
