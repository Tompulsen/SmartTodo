<template>
  <div class="planner-shell focus-shell">
    <aside class="desktop-rail" aria-label="主导航">
      <router-link to="/index" class="rail-brand" aria-label="SmartTodo 首页"><PlannerIcon name="tasks" /></router-link>
      <router-link class="rail-item" to="/index"><PlannerIcon name="calendar" /><span>计划</span></router-link>
      <router-link class="rail-item" to="/index?view=schedule"><PlannerIcon name="grid" /><span>视图</span></router-link>
      <router-link class="rail-item selected" to="/tomato" aria-current="page"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <button class="rail-item" @click="showRecords"><PlannerIcon name="chart" /><span>统计</span></button>
      <router-link class="rail-item rail-tools" to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </aside>
    <main class="planner-main focus-main">
      <header class="planner-header">
        <div class="brand-line"><router-link class="brand-word" to="/index">SmartTodo<span class="brand-dot"></span></router-link><span class="brand-subtitle">专注于此刻</span></div>
        <div class="header-actions"><span class="save-status" role="status"><PlannerIcon :name="pending ? 'clock' : error ? 'note' : 'saved'" />{{ pending ? '保存中' : error ? '连接异常' : auth.localMode ? '本地专注' : '已连接账号' }}</span><button class="icon-button" aria-label="专注设置" data-tip="专注设置" @click="openSettings"><PlannerIcon name="settings" /></button></div>
      </header>
      <div class="focus-page-heading">
        <div class="planner-tabs" role="tablist" aria-label="专注页面">
          <button role="tab" :aria-selected="pageTab === 'focus'" :class="{ active: pageTab === 'focus' }" @click="pageTab = 'focus'">专注</button>
          <button role="tab" :aria-selected="pageTab === 'presets'" :class="{ active: pageTab === 'presets' }" @click="pageTab = 'presets'">常用</button>
        </div>
        <span class="focus-date">{{ todayCaption }}</span>
      </div>
      <div v-if="error" class="planner-error" role="alert"><span>{{ error }}</span><button class="text-button" :disabled="pending || syncing" @click="refresh">重新连接</button></div>
      <div v-if="loading" class="planner-loading" role="status"><span class="loading-line"></span>正在读取专注状态</div>
      <div v-else class="focus-workspace">
        <section class="focus-stage" aria-label="专注计时器">
          <div v-show="pageTab === 'focus'" class="focus-timer-view">
            <div class="focus-mode-switch" role="group" aria-label="计时模式">
              <button v-for="item in modes" :key="item.value" :aria-pressed="mode === item.value" :class="{ selected: mode === item.value }"
                :disabled="active || pending" @click="mode = item.value">{{ item.label }}</button>
            </div>
            <button class="focus-plan-link" :disabled="active || pending" @click="openPlans">
              <PlannerIcon name="link" /><span>{{ selectedLink?.title || '关联计划' }}</span><PlannerIcon name="right" />
            </button>
            <span v-if="selectedLink" class="focus-plan-caption">{{ periodLabel(selectedLink.period) }}计划 · {{ selectedLink.section }}</span>
            <div v-else class="focus-plan-caption">自由专注</div>

            <div class="focus-dial" :class="{ resting: isResting, paused: session?.status === 'paused' && active }">
              <PlannerIcon name="leaf" class="focus-leaf" />
              <svg class="focus-ring" viewBox="0 0 360 360" aria-hidden="true">
                <circle cx="180" cy="180" r="161" class="focus-ring-border" />
                <circle cx="180" cy="180" r="161" class="focus-ring-track" />
                <circle cx="180" cy="180" r="161" class="focus-ring-progress" :stroke-dasharray="ringLength" :stroke-dashoffset="ringLength * (1 - progress)" />
              </svg>
              <div v-if="!active && mode !== 'stopwatch'" class="focus-duration">
                <button class="icon-button" aria-label="增加专注时长" title="增加一分钟" :disabled="pending || duration >= 180" @click="duration = Math.min(180, duration + 1)"><PlannerIcon name="up" /></button>
                <label><input v-model.number="duration" type="number" min="1" max="180" inputmode="numeric" aria-label="专注时长（分钟）" :disabled="pending" @change="normalizeDuration" /><span>分钟</span></label>
                <button class="icon-button" aria-label="减少专注时长" title="减少一分钟" :disabled="pending || duration <= 1" @click="duration = Math.max(1, duration - 1)"><PlannerIcon name="down" /></button>
              </div>
              <div v-else class="focus-countdown">
                <span class="focus-phase">{{ active ? isResting ? '休息时间' : session?.status === 'paused' ? '已暂停' : '专注中' : '正计时' }}</span>
                <strong role="timer" aria-live="off" :aria-label="`计时 ${displayTime}`" :class="{ 'with-hours': displayTime.length > 5 }">{{ displayTime }}</strong>
                <span>{{ active ? session?.mode === 'stopwatch' ? '已专注' : '剩余时间' : '从此刻开始' }}</span>
              </div>
            </div>
            <p class="focus-cycle">{{ isResting ? '休息一下，再继续' : mode === 'pomodoro' ? `专注 ${active ? Math.round((session?.duration || 0) / 60) : duration} 分钟 · 休息 ${settings.rest} 分钟` : mode === 'stopwatch' ? '自由专注' : `${active ? Math.round((session?.duration || 0) / 60) : duration} 分钟专注` }}</p>
            <div class="focus-primary-controls">
              <button class="focus-round-button" :class="{ 'audio-active': backgroundPlaying }" aria-label="选择专注音频" title="选择专注音频" @click="focusAudio?.open()"><PlannerIcon name="music" /></button>
              <button v-if="!active" class="focus-start-button" :disabled="pending || !!error" @click="start()"><PlannerIcon name="play" />{{ pending ? '正在开始' : '开始专注' }}</button>
              <button v-else class="focus-start-button" :disabled="pending" @click="command(session?.status === 'paused' ? 'resume' : 'pause')"><PlannerIcon :name="session?.status === 'paused' ? 'play' : 'pause'" />{{ session?.status === 'paused' ? isResting ? '继续休息' : '继续专注' : '暂停' }}</button>
              <button v-if="active" class="focus-round-button" aria-label="结束本次专注" title="结束本次专注" :disabled="pending" @click="dialog = 'finish'"><PlannerIcon name="stop" /></button>
              <button v-else class="focus-round-button focus-goal-button" aria-label="设置专注目标" title="设置专注目标" @click="openSettings"><PlannerIcon name="focus" /></button>
            </div>
            <FocusAudio ref="focusAudio" :ducked="alarmActive" @playing-change="backgroundPlaying = $event" />
            <button v-if="active && selectedLink" class="text-button focus-back-plan" @click="visitPlan"><PlannerIcon name="calendar" />查看关联计划</button>
            <div v-else class="focus-scene" aria-hidden="true"><img :src="isResting ? '/planner/rest.png' : '/planner/focus.png'" alt="" /><span class="focus-scene-line"></span><span class="focus-scene-caption">一点一滴，积累专注</span></div>
          </div>
          <div v-show="pageTab === 'presets'" class="focus-presets">
            <h1>常用专注</h1>
            <button v-for="preset in presets" :key="preset.title" class="focus-preset" :disabled="active || pending" @click="applyPreset(preset)">
              <span class="preset-symbol" :class="`color-${preset.color}`"><PlannerIcon :name="preset.icon" /></span>
              <span><strong>{{ preset.title }}</strong><small>{{ modeLabel(preset.mode) }} · {{ preset.minutes ? `${preset.minutes} 分钟` : '不限时长' }}</small></span><PlannerIcon name="right" />
            </button>
            <button v-if="active" class="outline-button" @click="pageTab = 'focus'"><PlannerIcon name="clock" />返回当前专注</button>
          </div>
        </section>

        <aside ref="recordsPanel" class="focus-records" aria-label="专注统计与记录">
          <header class="focus-summary-heading"><h2>{{ reportDay === today ? '今日专注' : '专注记录' }}</h2><label class="focus-record-date"><PlannerIcon name="calendar" /><input v-model="reportDay" type="date" aria-label="记录日期" :max="today" /></label></header>
          <span v-if="reportDay !== today" class="focus-history-date">{{ reportDay.replace(/-/g, '.') }}</span>
          <div class="focus-metrics"><div><strong>{{ Math.floor(report.totalMs / 60000) }}<small>分钟</small></strong><span>累计专注</span></div><div><strong>{{ report.count }}<small>次</small></strong><span>完成专注</span></div></div>
          <div v-if="reportDay === today" class="focus-goal">
            <div><span>每日目标</span><button @click="openSettings">{{ settings.goal }} 分钟<PlannerIcon name="edit" /></button></div>
            <progress :value="Math.min(report.totalMs / 60000, settings.goal)" :max="settings.goal" aria-label="每日专注目标进度"></progress>
            <span>{{ goalPercent }}% 已达成</span>
          </div>
          <div class="focus-records-title"><h3>专注记录</h3><span>{{ report.count }} 条</span></div>
          <p v-if="recordError" class="form-error" role="alert">{{ recordError }} <button class="text-button" @click="loadRecords">重试</button></p>
          <div v-if="!report.records.length && !recordError" class="focus-record-empty"><img src="/planner/rest.png" alt="" /><span>暂无专注记录</span></div>
          <ol v-else class="focus-record-list">
            <li v-for="record in report.records" :key="record.id">
              <span class="record-dot"><PlannerIcon name="check" /></span>
              <div><strong>{{ record.title || '自由专注' }}</strong><span>{{ modeLabel(record.mode) }} · {{ recordTime(record.startedAt) }} - {{ recordTime(record.finishedAt) }}</span><small v-if="record.link">{{ periodLabel(record.link.period) }}计划 · {{ record.link.section }}</small></div>
              <time>{{ durationText(record.elapsedMs) }}</time>
            </li>
          </ol>
          <router-link class="focus-legacy-link" to="/tomato/legacy"><PlannerIcon name="back" />旧版番茄任务与历史记录</router-link>
        </aside>
      </div>
    </main>
    <nav class="mobile-nav" aria-label="主导航">
      <router-link to="/index"><PlannerIcon name="calendar" /><span>计划</span></router-link>
      <router-link to="/index?view=schedule"><PlannerIcon name="grid" /><span>视图</span></router-link>
      <router-link to="/tomato" class="selected" aria-current="page"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <button @click="showRecords"><PlannerIcon name="chart" /><span>统计</span></button>
      <router-link to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </nav>
    <audio ref="alarm" class="focus-alarm" :src="alarmSound" preload="auto"></audio>

    <PlannerDialog :open="dialog === 'plans'" title="关联计划" @close="dialog = null">
      <div class="planner-form">
        <label>搜索任务<input v-model="search" type="search" placeholder="任务名称" /></label>
        <div class="focus-link-period" role="group" aria-label="关联计划周期"><button v-for="item in periods" :key="item.value" :aria-pressed="linkPeriod === item.value" :class="{ selected: linkPeriod === item.value }" @click="linkPeriod = item.value">{{ item.label }}计划</button></div>
        <div v-if="plansLoading" class="focus-link-empty" role="status">正在读取计划</div>
        <p v-else-if="plansError" class="form-error" role="alert">{{ plansError }}<button class="text-button" @click="loadPlans">重试</button></p>
        <div v-else class="focus-link-list">
          <button v-for="item in candidates" :key="item.taskId" :class="{ chosen: selectedLink?.taskId === item.taskId && selectedLink?.period === item.period }" @click="chooseLink(item)">
            <span><strong>{{ item.title }}</strong><small>{{ item.section }}</small></span><PlannerIcon :name="selectedLink?.taskId === item.taskId && selectedLink?.period === item.period ? 'check' : 'plus'" />
          </button><span v-if="!candidates.length" class="focus-link-empty">暂无符合条件的未完成任务</span>
        </div>
        <footer class="dialog-footer"><button class="text-button" @click="selectedLink = null; dialog = null">不关联计划</button><div class="dialog-footer-spacer"></div><button class="outline-button" @click="dialog = null">取消</button></footer>
      </div>
    </PlannerDialog>
    <PlannerDialog :open="dialog === 'settings'" title="专注设置" @close="dialog = null">
      <form class="planner-form" @submit.prevent="saveSettings">
        <label>番茄钟时长（分钟）<input v-model.number="settingsForm.pomodoro" type="number" min="1" max="180" required /></label>
        <label>休息时长（分钟）<input v-model.number="settingsForm.rest" type="number" min="1" max="60" required /></label>
        <label>每日目标（分钟）<input v-model.number="settingsForm.goal" type="number" min="5" max="1440" required /></label>
        <label class="check-label daily-setting"><span><PlannerIcon name="sound" />结束提示音</span><input v-model="settingsForm.sound" type="checkbox" role="switch" /></label>
        <button v-if="settingsForm.sound" type="button" class="text-button" @click="playAlarm(true)"><PlannerIcon name="play" />试听提示音</button>
        <footer class="dialog-footer"><div class="dialog-footer-spacer"></div><button class="primary-button" type="submit"><PlannerIcon name="check" />完成</button></footer>
      </form>
    </PlannerDialog>
    <PlannerDialog :open="dialog === 'finish'" :title="isResting ? '结束休息' : '结束本次专注'" :busy="pending" @close="dialog = null">
      <div class="planner-form">
        <p class="focus-finish-summary">{{ isResting ? '已休息' : '本次已专注' }} <strong>{{ durationText(elapsed) }}</strong></p>
        <p v-if="!isResting" class="focus-finish-task">{{ session?.title || '自由专注' }}</p>
        <footer class="dialog-footer"><button class="text-button danger-text" :disabled="pending" @click="command('discard')">放弃本次</button><div class="dialog-footer-spacer"></div><button class="outline-button" :disabled="pending" @click="dialog = null">继续</button><button class="primary-button" :disabled="pending" @click="command('finish')">{{ isResting ? '结束休息' : '结束并记录' }}</button></footer>
      </div>
    </PlannerDialog>
    <PlannerDialog :open="dialog === 'completed'" :title="session?.mode === 'break' ? '休息结束' : '本次专注已完成'" :busy="pending" @close="acknowledge">
      <div class="planner-form focus-completion">
        <span class="focus-completion-icon"><PlannerIcon name="check" /></span><strong>{{ durationText(session?.elapsedMs || 0) }}</strong><span>{{ session?.title || (session?.mode === 'break' ? '准备好开始下一轮了吗？' : '自由专注') }}</span>
        <footer class="dialog-footer"><button class="outline-button" :disabled="pending" @click="acknowledge">完成</button><button v-if="session?.mode === 'pomodoro'" class="primary-button" :disabled="pending" @click="start('break')"><PlannerIcon name="clock" />休息 {{ settings.rest }} 分钟</button><button v-else class="primary-button" :disabled="pending" @click="start()"><PlannerIcon name="play" />再来一轮</button></footer>
      </div>
    </PlannerDialog>
    <div v-if="toast" class="planner-toast" role="status">{{ toast }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/auth'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import PlannerDialog from '@/components/planner/PlannerDialog.vue'
import FocusAudio from '@/components/focus/FocusAudio.vue'
import { dayKey, planRequest, type DailyPlan, type PlanPeriod } from '@/components/planner/planner'
import { clockLabel, focusElapsed, focusSeconds, focusRequest, FocusRequestError, modeLabel,
  type FocusMode, type FocusLink, type FocusState, type FocusReport } from '@/components/focus/focus'
import alarmSound from '@/components/tomato/S01.wav'

const router = useRouter()
const modes: { value: Exclude<FocusMode, 'break'>; label: string }[] = [
  { value: 'stopwatch', label: '正计时' }, { value: 'pomodoro', label: '番茄钟' }, { value: 'countdown', label: '倒计时' }
]
const periods: { value: PlanPeriod; label: string }[] = [{ value: 'day', label: '日' }, { value: 'week', label: '周' }, { value: 'month', label: '月' }, { value: 'year', label: '年' }]
const periodLabel = (period: PlanPeriod) => periods.find(item => item.value === period)!.label
const presets: { title: string; mode: Exclude<FocusMode, 'break'>; minutes: number; icon: string; color: string }[] = [
  { title: '日常专注', mode: 'pomodoro', minutes: 25, icon: 'leaf', color: 'rose' },
  { title: '深度工作', mode: 'countdown', minutes: 50, icon: 'focus', color: 'sage' },
  { title: '阅读学习', mode: 'countdown', minutes: 30, icon: 'note', color: 'gold' },
  { title: '自由专注', mode: 'stopwatch', minutes: 0, icon: 'clock', color: 'blue' }
]
const settings = reactive({ pomodoro: 25, rest: 5, goal: 120, sound: true })
try {
  const saved = JSON.parse(localStorage.getItem('smarttodo-focus-settings-v1') || '{}')
  for (const [key, max] of [['pomodoro', 180], ['rest', 60], ['goal', 1440]] as const) {
    if (Number.isInteger(saved[key]) && saved[key] >= (key === 'goal' ? 5 : 1) && saved[key] <= max) settings[key] = saved[key]
  }
  if (typeof saved.sound === 'boolean') settings.sound = saved.sound
} catch { /* Local settings are optional. */ }
const mode = ref<Exclude<FocusMode, 'break'>>('pomodoro')
const settingsForm = ref({ ...settings })
const duration = ref(settings.pomodoro)
const state = ref<FocusState>({ revision: 0, session: null, serverNow: Date.now() })
const session = computed(() => state.value.session)
const active = computed(() => !!session.value && ['running', 'paused'].includes(session.value.status))
const isResting = computed(() => active.value && session.value?.mode === 'break')
const now = ref(Date.now())
const today = computed(() => dayKey(new Date(now.value)))
const todayCaption = computed(() => new Date(now.value).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }))
const elapsed = computed(() => session.value ? focusElapsed(session.value, now.value) : 0)
const displayTime = computed(() => active.value && session.value ? clockLabel(focusSeconds(session.value, now.value)) : '00:00')
const ringLength = 2 * Math.PI * 161
const progress = computed(() => !active.value ? (mode.value === 'stopwatch' ? 0 : Math.min(1, duration.value / 120)) :
  session.value?.duration ? elapsed.value / (session.value.duration * 1000) : (elapsed.value % 3600000) / 3600000)
const loading = ref(true)
const pending = ref(false)
const syncing = ref(false)
const error = ref('')
const toast = ref('')
const pageTab = ref<'focus' | 'presets'>('focus')
const dialog = ref<'plans' | 'settings' | 'finish' | 'completed' | null>(null)
const selectedLink = ref<FocusLink | null>(null)
const reportDay = ref(dayKey(new Date()))
const report = ref<FocusReport>({ records: [], totalMs: 0, count: 0 })
const recordError = ref('')
const recordsPanel = ref<HTMLElement | null>(null)
const goalPercent = computed(() => Math.min(100, Math.floor(report.value.totalMs / (settings.goal * 600))))
const plans = ref<DailyPlan[]>([])
const plansLoading = ref(false)
const plansError = ref('')
const linkPeriod = ref<PlanPeriod>('day')
const search = ref('')
const candidates = computed(() => plans.value.filter(plan => (plan.period || 'day') === linkPeriod.value)
  .flatMap(plan => plan.sections.flatMap(section => section.tasks.filter(task => !task.done && task.title.toLowerCase().includes(search.value.trim().toLowerCase()))
    .map(task => ({ period: plan.period || 'day', day: plan.day, taskId: task.id, title: task.title, section: section.title })))))
const alarm = ref<HTMLAudioElement | null>(null)
const focusAudio = ref<InstanceType<typeof FocusAudio>>()
const backgroundPlaying = ref(false)
const alarmActive = ref(false)
let timer: ReturnType<typeof setInterval>
let toastTimer: ReturnType<typeof setTimeout>
let soundTimer: ReturnType<typeof setTimeout>
let syncedAt = performance.now()
let serverAt = Date.now()
let lastRefresh = 0
let recordSequence = 0
let disposed = false
let acknowledgedId = ''
try { acknowledgedId = localStorage.getItem('smarttodo-focus-ack-v1') || '' } catch { /* Optional preference. */ }
function notify(message: string) { clearTimeout(toastTimer); toast.value = message; toastTimer = setTimeout(() => { toast.value = '' }, 3500) }
function normalizeDuration() { duration.value = Number.isFinite(duration.value) ? Math.min(180, Math.max(1, Math.round(duration.value))) : 25 }
function durationText(ms: number) { return ms < 60000 ? `${Math.floor(ms / 1000)} 秒` : `${Math.floor(ms / 60000)} 分 ${Math.floor(ms / 1000) % 60} 秒` }
function recordTime(ms: number) { return new Date(ms).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
function stopSound() { clearTimeout(soundTimer); alarm.value?.pause(); alarmActive.value = false }
function playAlarm(preview = false) {
  if (!alarm.value || (!settings.sound && !preview)) return
  stopSound()
  alarm.value.currentTime = 0
  alarm.value.volume = 0.5
  alarmActive.value = true
  void alarm.value.play().catch(() => notify('浏览器未允许播放提示音'))
  soundTimer = setTimeout(stopSound, 6000)
}
function acknowledge() {
  stopSound()
  if (session.value) {
    acknowledgedId = session.value.id
    try { localStorage.setItem('smarttodo-focus-ack-v1', acknowledgedId) } catch { /* Keep this tab's acknowledgement. */ }
  }
  dialog.value = null
}
function accept(result: FocusState) {
  if (disposed || result.revision < state.value.revision) return
  const previous = state.value.session
  state.value = result
  syncedAt = performance.now()
  serverAt = result.serverNow
  now.value = serverAt
  const current = result.session
  if (current && ['running', 'paused'].includes(current.status)) {
    if (current.mode !== 'break') {
      selectedLink.value = current.link
      mode.value = current.mode
      if (current.duration) duration.value = current.duration / 60
    }
  }
  if (current?.status === 'completed' && current.id !== acknowledgedId) {
    if (dialog.value !== 'completed') {
      dialog.value = 'completed'
      focusAudio.value?.close()
      if (previous?.id === current.id && previous.status === 'running') playAlarm()
      void loadRecords()
    }
  }
}
async function refresh() {
  if (syncing.value || pending.value || disposed) return
  syncing.value = true
  lastRefresh = performance.now()
  try { accept(await focusRequest<FocusState>('/state')); error.value = '' }
  catch { error.value = '专注状态同步失败，请检查本地服务后重试。' }
  finally { syncing.value = false; loading.value = false }
}
async function command(action: string, extra: Record<string, unknown> = {}) {
  if (pending.value || disposed) return
  pending.value = true
  try {
    const result = await focusRequest<FocusState>('/state', { action, revision: state.value.revision, id: session.value?.id, ...extra })
    dialog.value = null
    accept(result)
    error.value = ''
    if (action === 'finish') void loadRecords()
  } catch (err) {
    if (err instanceof FocusRequestError && err.status === 409) {
      accept(await focusRequest<FocusState>('/state').catch(() => state.value))
      notify('专注状态已在其他窗口更新，请确认后重试')
    } else if (err instanceof FocusRequestError && err.status === 400) {
      error.value = '无法开始：请检查时长，或重新选择关联任务。'
    } else error.value = '操作未确认，请重新连接后查看专注状态。'
  } finally { pending.value = false }
}
async function start(nextMode: FocusMode = mode.value) {
  normalizeDuration()
  if (dialog.value === 'completed') acknowledge()
  if (settings.sound && alarm.value) {
    const audio = alarm.value
    audio.volume = 0
    void audio.play().then(() => { audio.pause(); audio.currentTime = 0 }).catch(() => { /* Completion stays visible if audio is blocked. */ })
  }
  await command('start', { mode: nextMode, duration: nextMode === 'stopwatch' ? 0 : (nextMode === 'break' ? settings.rest : duration.value) * 60,
    link: nextMode === 'break' ? null : selectedLink.value })
}
async function loadRecords() {
  const sequence = ++recordSequence
  const day = reportDay.value
  try {
    const value = await focusRequest<FocusReport>(`/records?day=${day}&offset=${-new Date(`${day}T12:00:00`).getTimezoneOffset()}`)
    if (sequence === recordSequence && !disposed) { report.value = value; recordError.value = '' }
  } catch { if (sequence === recordSequence) recordError.value = '记录读取失败。' }
}
async function loadPlans() {
  plansLoading.value = true
  plansError.value = ''
  try { plans.value = await planRequest<DailyPlan[]>(`/agenda/${today.value}`) }
  catch { plansError.value = '计划读取失败，请重试。' }
  finally { plansLoading.value = false }
}
function openPlans() { search.value = ''; dialog.value = 'plans'; void loadPlans() }
function chooseLink(link: FocusLink) { selectedLink.value = link; dialog.value = null }
function visitPlan() {
  if (selectedLink.value) void router.push({ path: '/index', query: { period: selectedLink.value.period, date: selectedLink.value.day } })
}
function openSettings() { settingsForm.value = { ...settings }; dialog.value = 'settings' }
function saveSettings() {
  for (const [key, min, max] of [['pomodoro', 1, 180], ['rest', 1, 60], ['goal', 5, 1440]] as const) {
    const value = settingsForm.value[key]
    if (!Number.isInteger(value) || value < min || value > max) return
  }
  Object.assign(settings, settingsForm.value)
  if (!active.value && mode.value === 'pomodoro') duration.value = settings.pomodoro
  dialog.value = null
  stopSound()
}
async function showRecords() { await nextTick(); recordsPanel.value?.scrollIntoView({ block: 'start' }) }
function applyPreset(preset: typeof presets[number]) {
  mode.value = preset.mode
  duration.value = preset.minutes || settings.pomodoro
  pageTab.value = 'focus'
}
function visibilityChanged() { if (document.visibilityState === 'visible') { void refresh(); void loadRecords() } }
watch(mode, value => { if (!active.value && value === 'pomodoro') duration.value = settings.pomodoro })
watch(reportDay, () => { void loadRecords() })
watch(today, (day, previous) => { if (reportDay.value === previous) reportDay.value = day })
watch(settings, () => {
  try { localStorage.setItem('smarttodo-focus-settings-v1', JSON.stringify(settings)) } catch { /* The timer is stored on the server. */ }
  if (!settings.sound) stopSound()
})
onMounted(() => {
  document.title = '专注 - SmartTodo'
  void refresh()
  void loadRecords()
  document.addEventListener('visibilitychange', visibilityChanged)
  timer = setInterval(() => {
    now.value = serverAt + performance.now() - syncedAt
    const endReached = session.value?.status === 'running' && elapsed.value >= (session.value.duration || 86400) * 1000
    if (performance.now() - lastRefresh >= (endReached ? 1500 : 15000)) void refresh()
  }, 250)
})
onBeforeUnmount(() => {
  disposed = true
  clearInterval(timer)
  clearTimeout(toastTimer)
  stopSound()
  document.removeEventListener('visibilitychange', visibilityChanged)
  document.title = 'SmartTodo'
})
</script>

<style src="@/components/planner/planner.css"></style>
<style src="@/components/focus/focus.css"></style>
