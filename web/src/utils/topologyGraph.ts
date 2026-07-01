import { type TopologyConfig } from '../apis/topology'

export interface GraphNode { id: string; label: string }
export interface GraphEdge { source: string; target: string; label?: string }
export interface GraphData { nodes: GraphNode[]; edges: GraphEdge[] }

/**
 * 把后端扁平的拓扑配置行转成 G6 三层树图数据（project 根 → host → process）。
 *
 * 纯函数，G6-agnostic：只产出 { id, label }，不产坐标 / node.type（dagre 布局与
 * Topology.vue 后处理各自负责）。projectId 显式传入，故空数组也能建出根节点。
 *
 * 幂等去重：重复的 (hostId, process) 行不会产生重复节点或边。proc id 的两段经
 * encodeURIComponent 编码、并以 '/' 分隔防撞：encodeURIComponent 会把段内的 '/'
 * 转成 %2F，故分隔符必唯一，host/process 名含 '-' 时两段也不会串味。
 */
export function configRowsToGraph(
  rows: TopologyConfig[],
  projectId: string | number,
): GraphData {
  const rootId = `project-${projectId}`
  const nodes: GraphNode[] = [{ id: rootId, label: `项目 ${projectId}` }]
  const edges: GraphEdge[] = []
  const seen = new Set<string>([rootId])

  for (const row of rows) {
    // 空 hostId 无法构成有意义的 host 节点（且 `host-` id 会互撞）→ 跳整行。
    if (row.hostId === '') continue

    const hostId = `host-${encodeURIComponent(row.hostId)}`
    if (!seen.has(hostId)) {
      seen.add(hostId)
      nodes.push({ id: hostId, label: row.hostId })
      edges.push({ source: rootId, target: hostId })
    }

    // 空 process：只建/复用 host，不建 process 节点与 host→proc 边。
    if (row.process === '') continue

    const procId = `proc-${encodeURIComponent(row.hostId)}/${encodeURIComponent(row.process)}`
    if (!seen.has(procId)) {
      seen.add(procId)
      nodes.push({ id: procId, label: row.process })
      edges.push({ source: hostId, target: procId })
    }
  }

  return { nodes, edges }
}
