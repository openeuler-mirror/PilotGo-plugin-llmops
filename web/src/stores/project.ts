import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  type Project,
} from '@/apis/project'

/**
 * Pinia store for project state.
 *
 * Wraps the CRUD endpoints in `@/apis/project` and exposes the project list,
 * the currently selected project, plus shared loading / error flags so views
 * don't each have to reimplement request bookkeeping.
 */
export const useProjectStore = defineStore('project', () => {
  // ---- state ----
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- getters ----
  const projectCount = computed(() => projects.value.length)
  const hasProjects = computed(() => projects.value.length > 0)
  const getProjectById = computed(
    () => (id: number) => projects.value.find((p) => p.id === id) ?? null,
  )

  // ---- helpers ----
  function setError(e: unknown): void {
    error.value = e instanceof Error ? e.message : String(e)
  }

  function clearError(): void {
    error.value = null
  }

  function setCurrentProject(project: Project | null): void {
    currentProject.value = project
  }

  // ---- actions ----
  /** Load the full project list. */
  async function fetchProjects(): Promise<Project[]> {
    loading.value = true
    error.value = null
    try {
      projects.value = await listProjects()
      return projects.value
    } catch (e) {
      setError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /** Load a single project by id and mark it as the current selection. */
  async function fetchProject(id: number): Promise<Project> {
    loading.value = true
    error.value = null
    try {
      const project = await getProject(id)
      currentProject.value = project
      return project
    } catch (e) {
      setError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /** Create a project, then refresh the list. */
  async function addProject(payload: { name: string; desc?: string }): Promise<string> {
    loading.value = true
    error.value = null
    try {
      const message = await createProject(payload)
      projects.value = await listProjects()
      return message
    } catch (e) {
      setError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /** Update a project, then refresh the list and the current selection if affected. */
  async function editProject(
    id: number,
    payload: { name: string; desc?: string },
  ): Promise<string> {
    loading.value = true
    error.value = null
    try {
      const message = await updateProject(id, payload)
      projects.value = await listProjects()
      if (currentProject.value?.id === id) {
        currentProject.value = projects.value.find((p) => p.id === id) ?? currentProject.value
      }
      return message
    } catch (e) {
      setError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /** Delete a project, then refresh the list and clear the selection if it was removed. */
  async function removeProject(id: number): Promise<string> {
    loading.value = true
    error.value = null
    try {
      const message = await deleteProject(id)
      projects.value = await listProjects()
      if (currentProject.value?.id === id) {
        currentProject.value = null
      }
      return message
    } catch (e) {
      setError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    projects,
    currentProject,
    loading,
    error,
    // getters
    projectCount,
    hasProjects,
    getProjectById,
    // actions
    fetchProjects,
    fetchProject,
    addProject,
    editProject,
    removeProject,
    setCurrentProject,
    clearError,
  }
})
