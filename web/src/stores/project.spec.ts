import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useProjectStore } from './project'
import {
  listProjects, getProject, createProject, updateProject, deleteProject,
  type Project,
} from '@/apis/project'

vi.mock('@/apis/project')

// Project 工厂（字段全给：id/name/desc/created_at/updated_at）
const p = (id: number, name = `p${id}`): Project =>
  ({ id, name, desc: '', created_at: '', updated_at: '' })

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('getters', () => {
  it('projectCount 空为 0，填充后为 2', async () => {
    const store = useProjectStore()
    expect(store.projectCount).toBe(0)
    vi.mocked(listProjects).mockResolvedValue([p(1), p(2)])
    await store.fetchProjects()
    expect(store.projectCount).toBe(2)
  })

  it('hasProjects 空为 false，有数据为 true', async () => {
    const store = useProjectStore()
    expect(store.hasProjects).toBe(false)
    vi.mocked(listProjects).mockResolvedValue([p(1)])
    await store.fetchProjects()
    expect(store.hasProjects).toBe(true)
  })

  it('getProjectById 命中返回对象，未命中返回 null', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockResolvedValue([p(1), p(2)])
    await store.fetchProjects()
    expect(store.getProjectById(1)).toEqual(p(1))
    expect(store.getProjectById(999)).toBeNull()
  })
})

describe('helpers', () => {
  it('setCurrentProject 设值与清空', () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1))
    expect(store.currentProject).toEqual(p(1))
    store.setCurrentProject(null)
    expect(store.currentProject).toBeNull()
  })

  it('clearError 把 error 置 null', () => {
    const store = useProjectStore()
    store.error = 'x'
    store.clearError()
    expect(store.error).toBeNull()
  })
})

describe('fetchProjects', () => {
  it('成功填充 projects、返回值、loading 归位、error 清空', async () => {
    const store = useProjectStore()
    store.error = 'stale'
    const list = [p(1), p(2)]
    vi.mocked(listProjects).mockResolvedValue(list)
    const ret = await store.fetchProjects()
    expect(store.projects).toEqual(list)
    expect(ret).toBe(store.projects)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('失败 rethrow、setError、loading 归位、projects 保持原样', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockRejectedValue(new Error('boom'))
    await expect(store.fetchProjects()).rejects.toThrow('boom')
    expect(store.error).toBe('boom')
    expect(store.loading).toBe(false)
    expect(store.projects).toEqual([])
  })
})

describe('fetchProject', () => {
  it('成功设 currentProject、返回、loading 归位、error 清空', async () => {
    const store = useProjectStore()
    store.error = 'stale'
    vi.mocked(getProject).mockResolvedValue(p(1))
    const ret = await store.fetchProject(1)
    expect(store.currentProject).toEqual(p(1))
    expect(ret).toEqual(p(1))
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('失败 rethrow、setError、loading 归位、currentProject 不变', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(5))
    vi.mocked(getProject).mockRejectedValue(new Error('x'))
    await expect(store.fetchProject(1)).rejects.toThrow('x')
    expect(store.error).toBe('x')
    expect(store.loading).toBe(false)
    expect(store.currentProject).toEqual(p(5))
  })
})

describe('addProject', () => {
  it('成功调 create、刷新 list、返回 message、loading 归位', async () => {
    const store = useProjectStore()
    const payload = { name: 'new', desc: 'd' }
    vi.mocked(createProject).mockResolvedValue('created')
    vi.mocked(listProjects).mockResolvedValue([p(1)])
    const ret = await store.addProject(payload)
    expect(vi.mocked(createProject)).toHaveBeenCalledWith(payload)
    expect(vi.mocked(listProjects)).toHaveBeenCalledTimes(1)
    expect(store.projects).toEqual([p(1)])
    expect(ret).toBe('created')
    expect(store.loading).toBe(false)
  })

  it('失败 rethrow、刷新短路、projects 原样、loading 归位', async () => {
    const store = useProjectStore()
    vi.mocked(createProject).mockRejectedValue(new Error('e'))
    await expect(store.addProject({ name: 'x' })).rejects.toThrow('e')
    expect(vi.mocked(listProjects)).toHaveBeenCalledTimes(0)
    expect(store.projects).toEqual([])
    expect(store.loading).toBe(false)
  })
})

describe('editProject', () => {
  it('成功调 update、刷新 list、返回 message', async () => {
    const store = useProjectStore()
    const payload = { name: 'n', desc: 'd' }
    vi.mocked(updateProject).mockResolvedValue('updated')
    vi.mocked(listProjects).mockResolvedValue([p(1)])
    const ret = await store.editProject(1, payload)
    expect(vi.mocked(updateProject)).toHaveBeenCalledWith(1, payload)
    expect(vi.mocked(listProjects)).toHaveBeenCalledTimes(1)
    expect(ret).toBe('updated')
  })

  it('分支A：currentProject.id===id 时同步为刷新后的新对象', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1, 'old'))
    vi.mocked(updateProject).mockResolvedValue('updated')
    vi.mocked(listProjects).mockResolvedValue([p(1, 'new')])
    await store.editProject(1, { name: 'new' })
    expect(store.currentProject).toEqual(p(1, 'new'))
  })

  it('分支B：currentProject 不匹配时不动', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(2))
    vi.mocked(updateProject).mockResolvedValue('updated')
    vi.mocked(listProjects).mockResolvedValue([p(1, 'new')])
    await store.editProject(1, { name: 'new' })
    expect(store.currentProject).toEqual(p(2))
  })

  it('分支C：匹配但刷新后 list 不含该 id 时回退保留旧值', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1, 'old'))
    vi.mocked(updateProject).mockResolvedValue('updated')
    vi.mocked(listProjects).mockResolvedValue([p(2)])
    await store.editProject(1, { name: 'new' })
    expect(store.currentProject).toEqual(p(1, 'old'))
  })

  it('失败 rethrow、currentProject 与 projects 不变、loading 归位', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1))
    vi.mocked(updateProject).mockRejectedValue(new Error('e'))
    await expect(store.editProject(1, { name: 'x' })).rejects.toThrow('e')
    expect(vi.mocked(listProjects)).toHaveBeenCalledTimes(0)
    expect(store.currentProject).toEqual(p(1))
    expect(store.projects).toEqual([])
    expect(store.loading).toBe(false)
  })
})

describe('removeProject', () => {
  it('成功调 delete、刷新 list、返回 message', async () => {
    const store = useProjectStore()
    vi.mocked(deleteProject).mockResolvedValue('deleted')
    vi.mocked(listProjects).mockResolvedValue([])
    const ret = await store.removeProject(1)
    expect(vi.mocked(deleteProject)).toHaveBeenCalledWith(1)
    expect(vi.mocked(listProjects)).toHaveBeenCalledTimes(1)
    expect(ret).toBe('deleted')
  })

  it('分支A：currentProject.id===id 时清为 null', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1))
    vi.mocked(deleteProject).mockResolvedValue('deleted')
    vi.mocked(listProjects).mockResolvedValue([])
    await store.removeProject(1)
    expect(store.currentProject).toBeNull()
  })

  it('分支B：currentProject 不匹配时不动', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(2))
    vi.mocked(deleteProject).mockResolvedValue('deleted')
    vi.mocked(listProjects).mockResolvedValue([p(2)])
    await store.removeProject(1)
    expect(store.currentProject).toEqual(p(2))
  })

  it('失败 rethrow、currentProject 不变、loading 归位', async () => {
    const store = useProjectStore()
    store.setCurrentProject(p(1))
    vi.mocked(deleteProject).mockRejectedValue(new Error('e'))
    await expect(store.removeProject(1)).rejects.toThrow('e')
    expect(store.currentProject).toEqual(p(1))
    expect(store.loading).toBe(false)
  })
})

describe('setError 双分支（经 action 间接触发）', () => {
  it('Error 实例取 .message', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockRejectedValue(new Error('boom'))
    await expect(store.fetchProjects()).rejects.toBeTruthy()
    expect(store.error).toBe('boom')
  })

  it('非 Error 取 String(e)', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockRejectedValue('plain string')
    await expect(store.fetchProjects()).rejects.toBeTruthy()
    expect(store.error).toBe('plain string')
  })
})

describe('loading 时序', () => {
  it('成功路径：进行中 true、结束 false', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockResolvedValue([])
    const promise = store.fetchProjects()
    expect(store.loading).toBe(true)
    await promise
    expect(store.loading).toBe(false)
  })

  it('失败路径：reject 后归 false', async () => {
    const store = useProjectStore()
    vi.mocked(listProjects).mockRejectedValue(new Error('e'))
    const promise = store.fetchProjects()
    expect(store.loading).toBe(true)
    await expect(promise).rejects.toThrow('e')
    expect(store.loading).toBe(false)
  })
})
