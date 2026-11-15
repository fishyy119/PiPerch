import { type MaybeRefOrGetter, onBeforeUnmount, onMounted, toValue } from 'vue'

const EDITABLE_TARGET_SELECTOR = [
  'input',
  'textarea',
  'select',
  '[contenteditable=""]',
  '[contenteditable="true"]',
  '[contenteditable="plaintext-only"]',
  '[role="textbox"]',
  '[role="combobox"]',
  '[role="slider"]',
  '[role="spinbutton"]',
].join(',')

const OVERLAY_SELECTOR = '[role="dialog"], [role="alertdialog"], [role="menu"], [role="listbox"]'
const INACTIVE_SELECTOR = '[hidden], [inert], [aria-hidden="true"], [data-state="closed"]'

export interface KeyboardShortcut {
  key: string | readonly string[]
  action: () => void
  enabled?: MaybeRefOrGetter<boolean>
  repeat?: boolean
}

interface ShortcutRegistration {
  shortcuts: MaybeRefOrGetter<readonly KeyboardShortcut[]>
  isActive: () => boolean
}

// 注册项共用一个全局监听，最后一个组件卸载时释放。
const registrations = new Set<ShortcutRegistration>()

function handleKeydown(event: KeyboardEvent) {
  if (
    event.defaultPrevented ||
    event.isComposing ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    (event.target instanceof Element && !!event.target.closest(EDITABLE_TARGET_SELECTOR))
  ) {
    return
  }

  const matches = [...registrations]
    .filter((registration) => registration.isActive())
    .flatMap((registration) => toValue(registration.shortcuts))
    .filter((shortcut) => {
      const keys = typeof shortcut.key === 'string' ? [shortcut.key] : shortcut.key
      return (
        toValue(shortcut.enabled ?? true) &&
        keys.some((key) => key.toLowerCase() === event.key.toLowerCase())
      )
    })
  if (matches.length === 0) return

  event.preventDefault()
  // 重复绑定属于配置冲突，不依靠注册顺序决定执行哪个动作。
  if (matches.length > 1) {
    console.warn(`快捷键 ${event.key} 在当前上下文中重复注册`)
    return
  }
  const shortcut = matches[0]
  if (shortcut && (!event.repeat || shortcut.repeat !== false)) shortcut.action()
}

export function useKeyboardShortcuts(
  shortcuts: MaybeRefOrGetter<readonly KeyboardShortcut[]>,
  target?: MaybeRefOrGetter<HTMLElement | null>,
) {
  function isActive() {
    const element = target === undefined ? undefined : toValue(target)
    if (element !== undefined && (!element?.isConnected || element.closest(INACTIVE_SELECTOR))) {
      return false
    }
    // 页面快捷键避让所有弹层；组件快捷键只允许自身所在的弹层及其祖先。
    return ![...document.querySelectorAll(OVERLAY_SELECTOR)].some(
      (overlay) => !overlay.closest(INACTIVE_SELECTOR) && !overlay.contains(element ?? null),
    )
  }

  const registration = { shortcuts, isActive }
  onMounted(() => {
    registrations.add(registration)
    if (registrations.size === 1) window.addEventListener('keydown', handleKeydown)
  })
  onBeforeUnmount(() => {
    registrations.delete(registration)
    if (registrations.size === 0) window.removeEventListener('keydown', handleKeydown)
  })
  return isActive
}
