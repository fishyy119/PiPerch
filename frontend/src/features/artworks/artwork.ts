import { z } from 'zod'

export const artworkTypeSchema = z.enum(['illust', 'manga', 'ugoira'])
export type ArtworkType = z.infer<typeof artworkTypeSchema>
