import { z } from 'zod'

export const artworkTypeSchema = z.enum(['illust', 'manga', 'ugoira'])
export type ArtworkType = z.infer<typeof artworkTypeSchema>

const artworkTypeLabels: Record<ArtworkType, string> = {
  illust: '插画',
  manga: '漫画',
  ugoira: 'Ugoira',
}

export function artworkTypeLabel(type: ArtworkType) {
  return artworkTypeLabels[type]
}
