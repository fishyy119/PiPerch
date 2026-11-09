import type { ArtworkImage, ArtworkSummary } from '@/features/artworks/artworks-api'

export interface GalleryMediaItem {
  key: string
  artwork: ArtworkSummary
  media: ArtworkImage
  aspectRatio: number
}

export function galleryMediaItems(
  artworks: readonly ArtworkSummary[],
  media: readonly ArtworkImage[],
) {
  const mediaByArtwork = new Map<number, ArtworkImage[]>()
  for (const item of media) {
    const items = mediaByArtwork.get(item.artworkId) ?? []
    items.push(item)
    mediaByArtwork.set(item.artworkId, items)
  }
  return artworks.flatMap((artwork) =>
    (mediaByArtwork.get(artwork.localArtworkId) ?? [])
      .filter((item) =>
        artwork.artworkType === 'ugoira'
          ? item.role === 'ugoira'
          : item.role === 'page' && item.pageIndex !== null,
      )
      .sort((left, right) => (left.pageIndex ?? 0) - (right.pageIndex ?? 0))
      .map((item): GalleryMediaItem => ({
        key: `${String(item.artworkId)}:${item.role}:${String(item.pageIndex)}`,
        artwork,
        media: item,
        aspectRatio: item.width && item.height ? item.width / item.height : 1,
      })),
  )
}
