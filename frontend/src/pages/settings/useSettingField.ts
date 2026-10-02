import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { type Ref, ref, watch } from 'vue'

import { getSettings, patchSettings, type Settings } from '@/features/settings/settings-api'
import { errorMessage } from '@/shared/errors'
import { toast } from '@ui/toast'

const settingsQueryKey = ['settings'] as const

interface SettingFieldOptions<K extends keyof Settings, D> {
  label: string
  initialValue: D
  read?: (value: Settings[K]) => D
  write?: (value: D) => Settings[K]
  validate?: (value: D) => string | null
}

export function useSettingsQuery() {
  return useQuery({ queryKey: settingsQueryKey, queryFn: getSettings })
}

export function useSettingsLoadFeedback() {
  const settingsQuery = useSettingsQuery()
  watch(
    () => settingsQuery.error.value,
    (error) => {
      if (error) toast.error('加载设置失败', { description: errorMessage(error) })
    },
  )
}

export function useSettingField<K extends keyof Settings, D = Settings[K]>(
  key: K,
  options: SettingFieldOptions<K, D>,
) {
  const queryClient = useQueryClient()
  const settingsQuery = useSettingsQuery()
  const value = ref(options.initialValue) as Ref<D>
  const savedValue = ref(options.initialValue) as Ref<D>
  const read = options.read ?? ((nextValue: Settings[K]) => nextValue as unknown as D)
  const write = options.write ?? ((nextValue: D) => nextValue as unknown as Settings[K])

  const mutation = useMutation({
    mutationFn: (nextValue: D) => patchSettings({ [key]: write(nextValue) }),
    scope: { id: `setting-${key}` },
    onSuccess: (settings, submittedValue) => {
      const normalizedValue = read(settings[key])
      savedValue.value = normalizedValue
      if (Object.is(value.value, submittedValue)) value.value = normalizedValue
      queryClient.setQueryData<Settings>(settingsQueryKey, (current) =>
        current ? { ...current, [key]: settings[key] } : settings,
      )
      toast.success(`${options.label}已保存`)
    },
    onError: (error) => {
      toast.error(`${options.label}保存失败`, { description: errorMessage(error) })
    },
  })

  watch(
    () => settingsQuery.data.value?.[key],
    (nextValue) => {
      if (nextValue === undefined) return
      const nextDisplayValue = read(nextValue)
      const wasClean = Object.is(value.value, savedValue.value)
      savedValue.value = nextDisplayValue
      if (wasClean) value.value = nextDisplayValue
    },
    { immediate: true },
  )

  function save() {
    const validationMessage = options.validate?.(value.value)
    if (validationMessage) {
      toast.warning(`${options.label}未保存`, { description: validationMessage })
      return
    }
    if (Object.is(value.value, savedValue.value)) return
    mutation.mutate(value.value)
  }

  return { value, savedValue, save }
}
