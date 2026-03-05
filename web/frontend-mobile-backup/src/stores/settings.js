import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref({})
  const loading = ref(false)
  
  async function fetchSettings() {
    loading.value = true
    try {
      const res = await api.getSettings()
      settings.value = res.data
    } catch (error) {
      console.error('Failed to fetch settings:', error)
    } finally {
      loading.value = false
    }
  }
  
  async function saveSettings(newSettings) {
    try {
      await api.updateSettings(newSettings)
      settings.value = { ...settings.value, ...newSettings }
      return true
    } catch (error) {
      console.error('Failed to save settings:', error)
      return false
    }
  }
  
  return {
    settings,
    loading,
    fetchSettings,
    saveSettings
  }
})
