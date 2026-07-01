import { describe, it, expect } from 'vitest'

// vitest 脚手架自检（sanity check）。
// 首个真实业务单测待 topology 配置行→图映射函数抽离为可导出纯函数后补充
// （见 topology wire 计划）。
describe('vitest sanity', () => {
  it('runs and dedupes an array', () => {
    const unique = [...new Set([1, 2, 2, 3, 3, 3])]
    expect(unique).toEqual([1, 2, 3])
  })
})
