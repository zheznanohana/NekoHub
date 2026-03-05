import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useMessageStore = defineStore('message', () => {
  const messages = ref([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const wsConnected = ref(false)
  
  const unreadMessages = computed(() => messages.value.filter(m => !m.is_read))
  
  async function fetchMessages(limit = 50) {
    loading.value = true
    try {
      const res = await api.getMessages(limit)
      messages.value = res.data || []
      unreadCount.value = messages.value.filter(m => !m.is_read).length
      console.log('获取到消息:', messages.value.length, '条')
    } catch (error) {
      console.error('获取消息失败:', error)
      messages.value = []
      unreadCount.value = 0
    } finally {
      loading.value = false
    }
  }
  
  async function markRead(id) {
    try {
      await api.markRead(id)
      const msg = messages.value.find(m => m.id === id)
      if (msg) {
        msg.is_read = true
        unreadCount.value--
      }
    } catch (error) {
      console.error('Failed to mark read:', error)
    }
  }
  
  function addMessage(msg) {
    messages.value.unshift(msg)
    if (!msg.is_read) {
      unreadCount.value++
    }
  }
  
  function setWSStatus(connected) {
    wsConnected.value = connected
  }
  
  return {
    messages,
    unreadCount,
    loading,
    wsConnected,
    unreadMessages,
    fetchMessages,
    markRead,
    addMessage,
    setWSStatus
  }
})
