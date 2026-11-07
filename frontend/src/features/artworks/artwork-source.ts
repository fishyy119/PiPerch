import { z } from 'zod'

export const artworkSourceSchema = z.enum(['pixiv', 'fanbox'])
export type ArtworkSource = z.infer<typeof artworkSourceSchema>

export interface ArtworkIdentity {
  source: ArtworkSource
  remoteId: number
}

export type DownloadReference =
  { source: 'pixiv'; remoteId: number } | { source: 'fanbox'; remoteId: number; authorId: number }

export const libraryArtworkReferenceSchema = z.object({
  source: artworkSourceSchema,
  remoteId: z.number().int().positive(),
  localArtworkId: z.number().int().positive(),
})
export type LibraryArtworkReference = z.infer<typeof libraryArtworkReferenceSchema>

export function artworkReferenceKey(source: ArtworkSource, remoteId: number) {
  return `${source}:${String(remoteId)}`
}

export function artworkOriginalUrl(artwork: DownloadReference) {
  return artwork.source === 'fanbox'
    ? `https://pawchive.pw/fanbox/user/${String(artwork.authorId)}/post/${String(artwork.remoteId)}`
    : `https://www.pixiv.net/artworks/${String(artwork.remoteId)}`
}
