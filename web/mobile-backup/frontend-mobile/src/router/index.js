import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/components/Login.vue'
import MainLayout from '@/components/MainLayout.vue'
import Inbox from '@/components/Inbox.vue'
import AIChat from '@/components/AIChat.vue'
import Tasks from '@/components/Tasks.vue'
import Forward from '@/components/Forward.vue'
import RSS from '@/components/RSS.vue'
import Imap from '@/components/Imap.vue'
import Web3 from '@/components/Web3.vue'
import Settings from '@/components/Settings.vue'

const routes = [
  { 
    path: '/login', 
    name: 'Login', 
    component: Login,
    meta: { requiresGuest: true }
  },
  { 
    path: '/', 
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/inbox' },
      { path: 'inbox', name: 'Inbox', component: Inbox },
      { path: 'ai-chat', name: 'AIChat', component: AIChat },
      { path: 'tasks', name: 'Tasks', component: Tasks },
      { path: 'forward', name: 'Forward', component: Forward },
      { path: 'rss', name: 'RSS', component: RSS },
      { path: 'imap', name: 'Imap', component: Imap },
      { path: 'web3', name: 'Web3', component: Web3 },
      { path: 'settings', name: 'Settings', component: Settings }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  // 需要登录但未登录
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }
  
  // 已登录但访问登录页
  if (to.meta.requiresGuest && token) {
    next('/inbox')
    return
  }
  
  next()
})

export default router
