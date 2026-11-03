import { useLocalStorage } from '@vueuse/core'
import { readonly } from 'vue'

const MAX_HISTORY_ITEMS = 50

export function useInputHistory(scope: string) {
  const items = useLocalStorage<string[]>(`piperch.input-history.${scope}`, [])

  function record(value: string) {
    const input = value.trim()
    if (!input) return
    items.value = [input, ...items.value.filter((item) => item !== input)].slice(
      0,
      MAX_HISTORY_ITEMS,
    )
  }

  function remove(value: string) {
    items.value = items.value.filter((item) => item !== value)
  }

  return { items: readonly(items), record, remove }
}
