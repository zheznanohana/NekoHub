import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)
  
  async function fetchTasks() {
    loading.value = true
    try {
      const res = await api.getTasks()
      tasks.value = res.data
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    } finally {
      loading.value = false
    }
  }
  
  async function createTask(task) {
    try {
      const res = await api.createTask(task)
      tasks.value.push(res.data)
      return true
    } catch (error) {
      console.error('Failed to create task:', error)
      return false
    }
  }
  
  async function deleteTask(id) {
    try {
      await api.deleteTask(id)
      tasks.value = tasks.value.filter(t => t.id !== id)
      return true
    } catch (error) {
      console.error('Failed to delete task:', error)
      return false
    }
  }
  
  async function runTask(id) {
    try {
      await api.runTask(id)
      return true
    } catch (error) {
      console.error('Failed to run task:', error)
      return false
    }
  }
  
  return {
    tasks,
    loading,
    fetchTasks,
    createTask,
    deleteTask,
    runTask
  }
})
