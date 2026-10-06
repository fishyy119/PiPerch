import SelectionArea, { type SelectionEvent } from '@viselect/vanilla'
import { onBeforeUnmount, type Ref, watch } from 'vue'

import { useGallerySelectionStore } from '@/features/gallery/gallery-selection'

const SELECTABLE_SELECTOR = '[data-gallery-artwork-id]'
const REMOVING_CLASS = 'selection-area--removing'

function artworkIds(elements: Element[]) {
  return elements.flatMap((element) => {
    if (!(element instanceof HTMLElement)) return []
    const artworkId = Number(element.dataset.galleryArtworkId)
    return Number.isSafeInteger(artworkId) && artworkId > 0 ? [artworkId] : []
  })
}

export function useGalleryMarqueeSelection(grid: Ref<HTMLElement | null>) {
  const selection = useGallerySelectionStore()
  let selectionArea: SelectionArea | null = null
  let initialIds: number[] = []
  let intersectingIds: number[] = []
  let active = false
  let removing = false
  let suppressClick = false
  let suppressClickTimer: ReturnType<typeof setTimeout> | null = null

  function applySelection() {
    if (!active) return
    // 普通框选追加，按住 Shift 时从初始选择中移除。
    const nextIds = new Set(initialIds)
    intersectingIds.forEach((artworkId) => {
      if (removing) nextIds.delete(artworkId)
      else nextIds.add(artworkId)
    })
    selection.setSelected([...nextIds])
  }

  function setRemoving(value: boolean) {
    removing = value
    selectionArea?.getSelectionArea().classList.toggle(REMOVING_CLASS, value)
    applySelection()
  }

  function handleModifierChange(event: KeyboardEvent) {
    if (event.key === 'Shift') setRemoving(event.type === 'keydown')
  }

  function stopInteraction() {
    window.removeEventListener('keydown', handleModifierChange)
    window.removeEventListener('keyup', handleModifierChange)
    active = false
    initialIds = []
    intersectingIds = []
    setRemoving(false)
  }

  function clearClickSuppression() {
    suppressClick = false
    if (suppressClickTimer !== null) {
      clearTimeout(suppressClickTimer)
      suppressClickTimer = null
    }
  }

  function armClickSuppression() {
    clearClickSuppression()
    suppressClick = true
    suppressClickTimer = setTimeout(clearClickSuppression, 0)
  }

  function handleClick(event: MouseEvent) {
    if (!suppressClick) return
    event.preventDefault()
    event.stopPropagation()
    clearClickSuppression()
  }

  function handleBeforeStart({ event, selection: area }: SelectionEvent) {
    const target = event?.target
    if (!selection.enabled || (target instanceof Element && target.closest('button'))) {
      return false
    }
    area.clearSelection(true, true)
  }

  function handleStart({ event }: SelectionEvent) {
    initialIds = selection.selectedIds
    intersectingIds = []
    active = true
    setRemoving(event instanceof MouseEvent && event.shiftKey)
    window.addEventListener('keydown', handleModifierChange)
    window.addEventListener('keyup', handleModifierChange)
  }

  function handleMove({ store }: SelectionEvent) {
    if (!active) return
    intersectingIds = artworkIds(store.selected)
    applySelection()
  }

  function handleStop({ store }: SelectionEvent) {
    if (!active) return
    intersectingIds = artworkIds(store.selected)
    applySelection()
    armClickSuppression()
    stopInteraction()
  }

  function destroySelectionArea() {
    stopInteraction()
    clearClickSuppression()
    selectionArea?.destroy()
    selectionArea = null
  }

  function createSelectionArea(element: HTMLElement) {
    destroySelectionArea()
    selectionArea = new SelectionArea({
      container: document.body,
      selectables: SELECTABLE_SELECTOR,
      startAreas: [element],
      boundaries: [document.documentElement],
      selectionContainerClass: 'selection-area-container',
      behaviour: {
        intersect: 'touch',
        overlap: 'keep',
        startThreshold: { x: 5, y: 5 },
        scrolling: { startScrollMargins: { x: 0, y: 72 } },
      },
      features: {
        range: false,
        touch: false,
        singleTap: { allow: false },
      },
    })
      .on('beforestart', handleBeforeStart)
      .on('start', handleStart)
      .on('move', handleMove)
      .on('stop', handleStop)

    if (!selection.enabled) selectionArea.disable()
  }

  function reset() {
    selectionArea?.cancel()
    selectionArea?.clearSelection(true, true)
    stopInteraction()
    clearClickSuppression()
  }

  watch(grid, (element) => {
    if (element) createSelectionArea(element)
    else destroySelectionArea()
  })
  watch(
    () => selection.enabled,
    (enabled) => {
      if (!selectionArea) return
      if (enabled) selectionArea.enable()
      else {
        reset()
        selectionArea.disable()
      }
    },
  )
  onBeforeUnmount(destroySelectionArea)

  return { handleClick, reset }
}
