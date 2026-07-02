import { describe, it, expect } from 'vitest'
import { buildQueryString } from './queryString'

describe('buildQueryString', () => {
  it('returns empty string for empty params', () => {
    expect(buildQueryString({})).toBe('')
  })

  it('skips undefined, null, and empty values', () => {
    expect(
      buildQueryString({
        a: '1',
        b: undefined,
        c: null,
        d: '',
        e: 0,
      })
    ).toBe('a=1&e=0')
  })

  it('joins multiple params', () => {
    expect(buildQueryString({ page: 2, perpage: 10, q: 'hello' })).toBe(
      'page=2&perpage=10&q=hello'
    )
  })
})
