import { describe, it, expect } from 'vitest'
import { appendQueryString, buildQueryString } from './queryString'

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

describe('appendQueryString', () => {
  it('returns the original url when params are missing or empty', () => {
    expect(appendQueryString('/api/items')).toBe('/api/items')
    expect(appendQueryString('/api/items', {})).toBe('/api/items')
  })

  it('appends query params to a path', () => {
    expect(appendQueryString('/api/knowledge/download', { object: 'a/b.txt' })).toBe(
      '/api/knowledge/download?object=a%2Fb.txt'
    )
  })

  it('joins existing query params with &', () => {
    expect(appendQueryString('/api/items?sort=desc', { page: 2 })).toBe(
      '/api/items?sort=desc&page=2'
    )
  })
})
