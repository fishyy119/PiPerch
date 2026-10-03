import { onBeforeUnmount, onMounted } from 'vue'

const EDITABLE_TARGET_SELECTOR = [
  'input',
  'textarea',
  'select',
  '[contenteditable=""]',
  '[contenteditable="true"]',
  '[role="textbox"]',
  '[role="combobox"]',
  '[role="slider"]',
  '[role="spinbutton"]',
].join(',')

const ACTIVE_OVERLAY_SELECTOR = [
  '[role="dialog"]:not([aria-hidden="true"])',
  '[role="alertdialog"]:not([aria-hidden="true"])',
  '[role="menu"][data-state="open"]',
  '[role="listbox"][data-state="open"]',
].join(',')

interface PageKeyboardShortcutOptions {
  allowOverlay?: (overlay: Element) => boolean
}

function hasBlockingOverlay(allowOverlay?: (overlay: Element) => boolean) {
  return [...document.querySelectorAll(ACTIVE_OVERLAY_SELECTOR)].some(
    (overlay) => !allowOverlay?.(overlay),
  )
}

function shortcutIsBlocked(event: KeyboardEvent, allowOverlay?: (overlay: Element) => boolean) {
  if (
    event.defaultPrevented ||
    event.isComposing ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey
  ) {
    return true
  }

  if (event.target instanceof Element && event.target.closest(EDITABLE_TARGET_SELECTOR)) {
    return true
  }

  return hasBlockingOverlay(allowOverlay)
}

export function usePageKeyboardShortcuts(
  handler: (event: KeyboardEvent) => void,
  { allowOverlay }: PageKeyboardShortcutOptions = {},
) {
  const handleKeydown = (event: KeyboardEvent) => {
    if (!shortcutIsBlocked(event, allowOverlay)) handler(event)
  }

  onMounted(() => window.addEventListener('keydown', handleKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
}
