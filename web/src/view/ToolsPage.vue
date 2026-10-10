<template>
  <main class="account-screen">
    <div class="account-content tools-content">
      <header class="account-topbar"><router-link to="/index" class="account-brand">SmartTodo<span>.</span></router-link><router-link to="/index" class="account-back"><PlannerIcon name="back" />返回计划</router-link></header>
      <div class="account-heading"><div><p class="account-eyebrow">工作与生活</p><h1>工具箱</h1></div><router-link to="/settings" class="account-user"><PlannerIcon name="user" />{{ auth.user?.displayName || '设置' }}</router-link></div>
      <div class="tools-grid">
        <router-link v-for="tool in tools" :key="tool.path" :to="tool.path" class="tool-entry" :class="{ 'tool-settings': tool.path === '/settings' }">
          <PlannerIcon :name="tool.icon" /><div><h2>{{ tool.title }}</h2><p>{{ tool.description }}</p></div><PlannerIcon name="right" />
        </router-link>
      </div>
      <section v-if="recent.length" class="recent-notes"><h2>最近笔记</h2><div class="tools-grid">
        <router-link v-for="note in recent" :key="note.path" :to="note.path" class="tool-entry"><PlannerIcon name="note" /><div><h2>{{ note.title }}</h2></div><PlannerIcon name="right" /></router-link>
      </div></section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { auth } from '@/auth'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'

const recent = ref<{ title: string; path: string }[]>([])
const tools = computed(() => [
  { title: '设置', path: '/settings', icon: 'settings', description: '个人资料、计划偏好与账号安全' },
  { title: '待办事项', path: '/todo', icon: 'tasks', description: '待办、笔记与附件' },
  { title: '专注时钟', path: '/tomato', icon: 'clock', description: '专注计时与白噪音' },
  { title: '私人助理', path: '/assistant', icon: 'note', description: '对话与计划整理' },
  { title: '体重记录', path: '/weight/record', icon: 'chart', description: '记录体重变化' },
  { title: '运动指导', path: '/exercise', icon: 'focus', description: '运动与日常训练' },
  { title: '体重计划', path: '/weight/plan', icon: 'calendar', description: '目标与进度' },
  { title: '打卡记录', path: '/checkin', icon: 'complete', description: '每日习惯与坚持' },
  { title: '今日数据', path: '/summary/today', icon: 'grid', description: '回顾今天的安排' },
  { title: '长期数据', path: '/summary/longterm', icon: 'chart', description: '查看长期积累' },
  ...(auth.user?.isAdmin ? [{ title: '系统日志', path: '/log', icon: 'list', description: '运行状态与事件' }] : [])
])
onMounted(async () => {
  try {
    const result = await axios.post('/item/recentNote')
    recent.value = Array.isArray(result.data) ? result.data.filter(item => typeof item.path === 'string' && /^\/note\/\d+$/.test(item.path)) : []
  } catch { recent.value = [] }
})
</script>

<style src="@/components/account/account.css"></style>
