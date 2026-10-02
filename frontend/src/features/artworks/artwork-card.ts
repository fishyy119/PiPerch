import type { RouteLocationRaw } from 'vue-router'

export type ArtworkCardTarget =
  { kind: 'route'; to: RouteLocationRaw } | { kind: 'external'; href: string }

export type ArtworkPreviewUrlResolver = (
  pageIndex: number,
) => string | null | Promise<string | null>
