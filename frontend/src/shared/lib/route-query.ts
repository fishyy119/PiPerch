import type { LocationQueryValue } from 'vue-router'

/**
 * 将 Vue Router 查询参数规范为单个字符串。
 * 同名参数出现多次时取首项，参数不存在或值为 null 时返回空字符串。
 */
export function firstQueryValue(value: LocationQueryValue | LocationQueryValue[] | undefined) {
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '')
}
