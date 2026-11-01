import type { RouteLocationRaw } from 'vue-router'

import type { ArtworkType } from '@/features/artworks/artwork'

export type ArtworkCardTarget =
  { kind: 'route'; to: RouteLocationRaw } | { kind: 'external'; href: string }

export type ArtworkPreviewUrlResolver = (
  pageIndex: number,
) => string | null | Promise<string | null>

export function localArtworkPreviewUrl(
  artworkId: number,
  artworkType: ArtworkType,
  pageIndex: number,
) {
  return artworkType === 'ugoira'
    ? `/api/artworks/${String(artworkId)}/cover`
    : `/api/artworks/${String(artworkId)}/pages/${String(pageIndex)}`
}
