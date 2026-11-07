export function mergeMarqueeSelection<Item>(
  initial: readonly Item[],
  intersecting: readonly Item[],
  getKey: (item: Item) => string,
  removing: boolean,
) {
  const next = new Map(initial.map((item) => [getKey(item), item]))
  for (const item of intersecting) {
    const key = getKey(item)
    if (removing) next.delete(key)
    else next.set(key, item)
  }
  return [...next.values()]
}
