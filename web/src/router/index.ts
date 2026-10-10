import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/view/LoginPage.vue'
import Todo from '@/view/TodoPage.vue'
import Message from '@/view/MessagePage.vue'
import TomatoPage from '@/view/TomatoPage.vue'
import FocusPage from '@/view/FocusPage.vue'
import WeightRecordPage from '@/view/WeightRecordPage.vue'
import Checkin from '@/view/CheckinPage.vue'
import Assistant from '@/view/AssistantPage.vue'
import Index from '@/view/IndexPage.vue'
import ExercisePage from '@/view/ExercisePage.vue'
import { isLocalMode } from '@/local-mode'
import { auth, loadSession } from '@/auth'

const WeightPlanPage = () => import('@/view/WeightPlanPage.vue')
const TodaySummaryPage = () => import('@/view/TodaySummaryPage.vue')
const LongSummaryPage = () => import('@/view/LongSummaryPage.vue')
const ToolsPage = () => import('@/view/ToolsPage.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/index' },
    { path: '/index', component: Index },
    { path: '/tools', component: ToolsPage },
    { path: '/login', component: Login },
    { path: '/register', component: Login },
    { path: '/settings', component: () => import('@/view/SettingsPage.vue') },
    { path: '/tools/admin', component: () => import('@/view/AdminPage.vue'), meta: { requiresAdmin: true } },
    { path: '/todo', component: Todo },
    { path: '/note/:id', component: Todo },
    { path: '/log/', component: Message },
    { path: '/tomato', component: FocusPage },
    { path: '/tomato/legacy', component: TomatoPage },
    { path: '/assistant', component: Assistant },
    { path: '/checkin', component: Checkin },
    { path: '/summary/today', component: TodaySummaryPage },
    { path: '/summary/longterm', component: LongSummaryPage },
    { path: '/weight/plan', component: WeightPlanPage },
    { path: '/weight/record', component: WeightRecordPage },
    { path: '/exercise', component: ExercisePage }
  ]
})

router.beforeEach(async (to) => {
  if (!auth.ready) await loadSession()
  const publicPage = ['/login', '/register'].includes(to.path)
  if ((isLocalMode || auth.user) && publicPage) {
    return { path: '/index', replace: true }
  }
  if (!isLocalMode && !auth.user && !publicPage) {
    return { path: '/login', query: { redirect: to.fullPath }, replace: true }
  }
  if (to.meta.requiresAdmin && (auth.localMode || !auth.user?.isAdmin)) {
    return { path: '/tools', replace: true }
  }
})

export default router
