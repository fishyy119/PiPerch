import { computed, nextTick, type Ref, ref, watch } from 'vue'

interface AutocompleteStateOptions {
  model: Ref<string>
  open: Ref<boolean>
  options: () => readonly string[]
  disabled: () => boolean
}

export function useAutocomplete({ model, open, options, disabled }: AutocompleteStateOptions) {
  const inputValue = ref(model.value)
  const query = ref(model.value)
  const isComposing = ref(false)
  const highlightedValue = ref<string>()
  const filteredOptions = computed(() => {
    const keyword = query.value.normalize('NFC').toLowerCase()
    return options().filter((option) => option.normalize('NFC').toLowerCase().includes(keyword))
  })
  const visible = computed(() => open.value && !disabled() && filteredOptions.value.length > 0)

  watch(model, (value) => {
    if (isComposing.value) return
    inputValue.value = value
    query.value = value
  })

  watch(
    [filteredOptions, visible],
    ([items, isVisible]) => {
      if (!isVisible) highlightedValue.value = undefined
      else if (highlightedValue.value === undefined || !items.includes(highlightedValue.value)) {
        highlightedValue.value = items[0]
      }
    },
    { immediate: true, flush: 'sync' },
  )

  watch(disabled, (isDisabled) => {
    if (isDisabled) open.value = false
  })

  function setOpen(value: boolean) {
    open.value = value && !disabled()
  }

  function updateInput(value: string | number) {
    inputValue.value = String(value)
    if (isComposing.value) return
    query.value = inputValue.value
    model.value = inputValue.value
    setOpen(true)
  }

  function startComposition() {
    isComposing.value = true
  }

  function finishComposition(value: string) {
    // 组合输入结束的同一轮事件中，回车仍交由输入法处理。
    void nextTick(() => {
      isComposing.value = false
      updateInput(value)
    })
  }

  function select(value: string) {
    if (isComposing.value || !visible.value || !filteredOptions.value.includes(value)) return false
    setOpen(false)
    inputValue.value = value
    query.value = value
    model.value = value
    return true
  }

  function moveHighlight(direction: 1 | -1) {
    const wasVisible = visible.value
    setOpen(true)
    const items = filteredOptions.value
    const index = wasVisible ? items.indexOf(highlightedValue.value ?? '') : -1
    const nextIndex =
      index < 0
        ? direction === 1
          ? 0
          : items.length - 1
        : Math.min(Math.max(index + direction, 0), items.length - 1)
    highlightedValue.value = items[nextIndex]
  }

  function handleKeydown(event: KeyboardEvent) {
    if (
      disabled() ||
      isComposing.value ||
      event.isComposing ||
      event.ctrlKey ||
      event.altKey ||
      event.metaKey
    )
      return

    switch (event.key) {
      case 'ArrowDown':
      case 'ArrowUp':
        if (event.shiftKey) return
        event.preventDefault()
        moveHighlight(event.key === 'ArrowDown' ? 1 : -1)
        break
      case 'Tab':
        if (
          !event.shiftKey &&
          highlightedValue.value !== undefined &&
          select(highlightedValue.value)
        ) {
          event.preventDefault()
        }
        break
      case 'Escape':
        if (!visible.value) return
        event.preventDefault()
        event.stopPropagation()
        setOpen(false)
        break
      case 'Enter':
        // 保留表单原生提交，不把高亮候选替换到当前输入中。
        setOpen(false)
        break
    }
  }

  return {
    inputValue,
    filteredOptions,
    highlightedValue,
    visible,
    setOpen,
    updateInput,
    startComposition,
    finishComposition,
    select,
    handleKeydown,
  }
}
