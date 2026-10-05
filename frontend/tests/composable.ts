import { render, type RenderOptions } from '@testing-library/vue'
import { defineComponent } from 'vue'

export function renderComposable<T>(
  setup: () => T,
  plugins: NonNullable<RenderOptions<unknown>['global']>['plugins'] = [],
) {
  let result!: T
  const view = render(
    defineComponent({
      setup() {
        result = setup()
        return () => null
      },
    }),
    { global: { plugins } },
  )
  return { result, unmount: () => view.unmount() }
}
