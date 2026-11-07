import type { ArtworkIdentity, DownloadReference } from '@/features/artworks/artwork-source'
import {
  discover,
  type DiscoveryItem,
  listArtworkPreviewUrls,
} from '@/features/discovery/discovery-api'

export interface DownloadPreview extends ArtworkIdentity {
  thumbnailUrl: string | null
  title?: string
}

export function discoveryPreview(item: DiscoveryItem): DownloadPreview {
  return {
    source: item.source,
    remoteId: item.remoteId,
    thumbnailUrl: item.thumbnailUrl,
    title: item.title,
  }
}

export async function loadDownloadPreviews(
  references: readonly DownloadReference[],
): Promise<DownloadPreview[]> {
  const pixiv = references.filter((item) => item.source === 'pixiv')
  const fanbox = references.filter((item) => item.source === 'fanbox')
  const [pixivPreviews, fanboxPreviews] = await Promise.all([
    pixiv.length
      ? discover({
          sourceType: 'artwork',
          inputs: pixiv.map((item) => String(item.remoteId)),
          page: 0,
        }).then((result) => result.items.map(discoveryPreview))
      : [],
    Promise.all(
      fanbox.map(async (item): Promise<DownloadPreview> => {
        const urls = await listArtworkPreviewUrls(item)
        return { source: item.source, remoteId: item.remoteId, thumbnailUrl: urls[0] ?? null }
      }),
    ),
  ])
  return [...pixivPreviews, ...fanboxPreviews]
}
