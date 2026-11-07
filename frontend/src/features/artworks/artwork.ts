import { z } from 'zod'

export const artworkTypeSchema = z.enum(['illust', 'manga', 'ugoira', 'fanbox'])
export type ArtworkType = z.infer<typeof artworkTypeSchema>

const artworkTypeLabels: Record<ArtworkType, string> = {
  illust: '插画',
  manga: '漫画',
  ugoira: 'Ugoira',
  fanbox: 'FANBOX',
}

export function artworkTypeLabel(type: ArtworkType) {
  return artworkTypeLabels[type]
}
