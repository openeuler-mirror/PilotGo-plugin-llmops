import { describe, it, expect } from 'vitest'
import { configRowsToGraph } from './topologyGraph'
import { type TopologyConfig } from '../apis/topology'

// 便捷构造 TopologyConfig 行（只关心 hostId/process，其余字段填空）。
const row = (hostId: string, process: string): TopologyConfig => ({
  id: `${hostId}:${process}`,
  projectId: 7,
  hostId,
  process,
  createdAt: '',
  updatedAt: '',
})

describe('configRowsToGraph', () => {
  it('空数组返回仅根节点', () => {
    const g = configRowsToGraph([], 7)
    expect(g.nodes).toEqual([{ id: 'project-7', label: '项目 7' }])
    expect(g.edges).toEqual([])
  })

  it('单行产出 3 节点 2 边', () => {
    const g = configRowsToGraph([row('h1', 'p1')], 7)
    expect(g.nodes).toEqual([
      { id: 'project-7', label: '项目 7' },
      { id: 'host-h1', label: 'h1' },
      { id: 'proc-h1/p1', label: 'p1' },
    ])
    expect(g.edges).toEqual([
      { source: 'project-7', target: 'host-h1' },
      { source: 'host-h1', target: 'proc-h1/p1' },
    ])
  })

  it('同 host 多 process 时 host 去重', () => {
    const g = configRowsToGraph([row('h1', 'p1'), row('h1', 'p2')], 7)
    expect(g.nodes.filter((n) => n.id === 'host-h1')).toHaveLength(1)
    expect(g.nodes.filter((n) => n.id.startsWith('proc-'))).toHaveLength(2)
    expect(g.edges.filter((e) => e.source === 'project-7' && e.target === 'host-h1')).toHaveLength(1)
    expect(g.edges.filter((e) => e.source === 'host-h1')).toHaveLength(2)
  })

  it('多 host 都挂到根', () => {
    const g = configRowsToGraph([row('h1', 'p1'), row('h2', 'p2')], 7)
    expect(g.nodes.filter((n) => n.id === 'host-h1')).toHaveLength(1)
    expect(g.nodes.filter((n) => n.id === 'host-h2')).toHaveLength(1)
    expect(g.edges.filter((e) => e.source === 'project-7' && e.target === 'host-h1')).toHaveLength(1)
    expect(g.edges.filter((e) => e.source === 'project-7' && e.target === 'host-h2')).toHaveLength(1)
  })

  it('完全重复行幂等去重', () => {
    const single = configRowsToGraph([row('h1', 'p1')], 7)
    const dup = configRowsToGraph([row('h1', 'p1'), row('h1', 'p1')], 7)
    expect(dup).toEqual(single)
  })

  it('process 空串时只建 host 不建 proc', () => {
    const g = configRowsToGraph([row('h1', '')], 7)
    expect(g.nodes).toContainEqual({ id: 'host-h1', label: 'h1' })
    expect(g.edges).toContainEqual({ source: 'project-7', target: 'host-h1' })
    expect(g.nodes.filter((n) => n.id.startsWith('proc-'))).toHaveLength(0)
    expect(g.edges.filter((e) => e.source === 'host-h1')).toHaveLength(0)
  })

  it('hostId 空串时整行跳过', () => {
    const g = configRowsToGraph([row('', 'p1')], 7)
    expect(g.nodes).toEqual([{ id: 'project-7', label: '项目 7' }])
    expect(g.edges).toEqual([])
  })

  it('projectId number 与 string 产出同 id', () => {
    const num = configRowsToGraph([], 7)
    const str = configRowsToGraph([], '7')
    expect(num.nodes[0]).toEqual({ id: 'project-7', label: '项目 7' })
    expect(str.nodes[0]).toEqual({ id: 'project-7', label: '项目 7' })
  })

  it('hostId/process 含连字符不串味（encodeURIComponent 防撞回归）', () => {
    const g = configRowsToGraph([row('a-b', 'c'), row('a', 'b-c')], 7)
    const procIds = g.nodes.filter((n) => n.id.startsWith('proc-')).map((n) => n.id)
    expect(procIds).toHaveLength(2)
    expect(procIds[0]).not.toBe(procIds[1])
    expect(g.edges.filter((e) => e.source.startsWith('host-') && e.target.startsWith('proc-'))).toHaveLength(2)
  })

  it('不产出坐标与 node.type', () => {
    const g = configRowsToGraph([row('h1', 'p1')], 7)
    const node = g.nodes[1]
    const edge = g.edges[0]
    expect(node).toBeDefined()
    expect(edge).toBeDefined()
    expect(Object.keys(node!).sort()).toEqual(['id', 'label'])
    expect(Object.keys(edge!).sort()).toEqual(['source', 'target'])
  })
})
