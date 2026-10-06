import SelectionArea, { type SelectionEvent } from '@viselect/vanilla'
import { onBeforeUnmount, type Ref, watch } from 'vue'

const SELECTABLE_SELECTOR = '[data-selection-id]'
const REMOVING_CLASS = 'selection-area--removing'
const IGNORED_START_SELECTOR = 'button, input, select, textarea, [data-selection-ignore]'

let nextScopeId = 0

interface MarqueeSelectionOptions {
  selectedIds: () => readonly number[]
  setSelectedIds: (artworkIds: readonly number[]) => void
  enabled?: () => boolean
  canStart?: (event: MouseEvent) => boolean
}

function selectionIds(elements: Element[]) {
  return elements.flatMap((element) => {
    if (!(element instanceof HTMLElement)) return []
    const selectionId = Number(element.dataset.selectionId)
    return Number.isSafeInteger(selectionId) && selectionId > 0 ? [selectionId] : []
  })
}

export function useMarqueeSelection(
  root: Ref<HTMLElement | null>,
  options: MarqueeSelectionOptions,
) {
  const scopeId = `marquee-${String(nextScopeId++)}`
  let selectionRoot: HTMLElement | null = null
  let selectionArea: SelectionArea | null = null
  let initialIds: number[] = []
  let intersectingIds: number[] = []
  let active = false
  let removing = false
  let suppressClick = false
  let suppressClickTimer: ReturnType<typeof setTimeout> | null = null

  function isEnabled() {
    return options.enabled?.() ?? true
  }

  function applySelection() {
    if (!active) return
    // 普通框选追加，按住 Shift 时从初始选择中移除。
    const nextIds = new Set(initialIds)
    intersectingIds.forEach((selectionId) => {
      if (removing) nextIds.delete(selectionId)
      else nextIds.add(selectionId)
    })
    options.setSelectedIds([...nextIds])
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
    if (
      !isEnabled() ||
      !(event instanceof MouseEvent) ||
      !(target instanceof Element) ||
      target.closest(IGNORED_START_SELECTOR) ||
      (target.closest('a, img') && !target.closest(SELECTABLE_SELECTOR)) ||
      options.canStart?.(event) === false
    ) {
      return false
    }
    area.clearSelection(true, true)
  }

  function handleStart({ event }: SelectionEvent) {
    initialIds = [...options.selectedIds()]
    intersectingIds = []
    active = true
    setRemoving(event instanceof MouseEvent && event.shiftKey)
    window.addEventListener('keydown', handleModifierChange)
    window.addEventListener('keyup', handleModifierChange)
  }

  function handleMove({ store }: SelectionEvent) {
    if (!active) return
    intersectingIds = selectionIds(store.selected)
    applySelection()
  }

  function handleStop({ store }: SelectionEvent) {
    if (!active) return
    intersectingIds = selectionIds(store.selected)
    applySelection()
    armClickSuppression()
    stopInteraction()
  }

  function destroySelectionArea() {
    stopInteraction()
    clearClickSuppression()
    selectionArea?.destroy()
    selectionArea = null
    if (selectionRoot?.dataset.marqueeSelectionScope === scopeId) {
      delete selectionRoot.dataset.marqueeSelectionScope
    }
    selectionRoot = null
  }

  function createSelectionArea(element: HTMLElement) {
    destroySelectionArea()
    selectionRoot = element
    element.dataset.marqueeSelectionScope = scopeId
    selectionArea = new SelectionArea({
      container: document.body,
      selectables: `[data-marquee-selection-scope="${scopeId}"] ${SELECTABLE_SELECTOR}`,
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

    if (!isEnabled()) selectionArea.disable()
  }

  function reset() {
    selectionArea?.cancel()
    selectionArea?.clearSelection(true, true)
    stopInteraction()
    clearClickSuppression()
  }

  watch(root, (element) => {
    if (element) createSelectionArea(element)
    else destroySelectionArea()
  })
  watch(
    () => isEnabled(),
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
