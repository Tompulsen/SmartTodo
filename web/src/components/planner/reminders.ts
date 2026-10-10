import { reactive, watch } from 'vue'
import { auth } from '@/auth'
import { nativeBridge, nativeScheduler, nativeAlarmPlan, nativeTag, type NativeAlarm } from './native-reminders'
import { dayKey, shiftDay, clonePlan, planPath, planRequest, type DailyPlan } from './planner'
import {
  actOnReminders, readReminderRecords, reconcileReminders, reminderHref, reminderOccurrences, reminderStorageKey,
  type ReminderOccurrence, type ReminderRecords
} from './reminder-state'

type Permission = NotificationPermission | 'unsupported'
export const reminderState = reactive({
  owner: '', pending: [] as ReminderOccurrence[], snoozed: [] as ReminderOccurrence[],
  next: null as ReminderOccurrence | null, permission: 'unsupported' as Permission,
  open: false, settingsOpen: false, testing: false, enabling: false, testOpen: false,
  sound: true, error: '', deliveryError: '', notice: '', checkedAt: 0, busyKey: '',
  storageAvailable: true, native: false, nativeReady: false, exact: false, nativeCount: 0
})
let records: ReminderRecords = {}
let plans: DailyPlan[] = []
let loadedAt = 0
let loadedDay = ''
let generation = 0
let inFlight: number | null = null
let retrySystemAt = 0
let timer: ReturnType<typeof setInterval> | undefined
let stopAuthWatch: (() => void) | undefined
let registration: Promise<ServiceWorkerRegistration | null> | null = null
let audio: AudioContext | null = null
let collapsed = false
let visibleSignature = ''
let forceRefresh = false
let futurePlans: DailyPlan[] = []
let futureLoadedAt = 0
let futureDay = ''
let nativeSignature = ''
const NATIVE_LEDGER = 'smarttodo-native-alarms-v1'
const desktopNotifications = new Map<Notification, string>()

function permission(): Permission {
  try {
    const bridge = nativeBridge()
    reminderState.native = !!bridge
    reminderState.nativeReady = !!nativeScheduler()
    reminderState.exact = !!bridge?.canScheduleExactAlarms()
    if (bridge) return bridge.getNotificationPermissionState()
  } catch { return 'unsupported' }
  return typeof Notification === 'undefined' ? 'unsupported' : Notification.permission
}
function persist() {
  try {
    localStorage.setItem(reminderStorageKey(reminderState.owner), JSON.stringify(records))
    reminderState.storageAvailable = true
  } catch { reminderState.storageAvailable = false }
}
function read() {
  try {
    const raw = localStorage.getItem(reminderStorageKey(reminderState.owner))
    if (raw !== null) records = readReminderRecords(raw, Date.now())
  } catch { reminderState.storageAvailable = false }
}
async function locked<T>(work: () => Promise<T> | T): Promise<T> {
  if (navigator.locks) return navigator.locks.request(reminderStorageKey(reminderState.owner), work)
  return work()
}
function syncQueue() {
  const before = JSON.stringify(records)
  const result = reconcileReminders(reminderOccurrences(plans), records, Date.now())
  records = result.records
  reminderState.pending = result.pending
  reminderState.snoozed = result.snoozed
  reminderState.next = reminderOccurrences(plans).find(item => item.dueAt > Date.now()) || null
  const signature = result.pending.map(item => `${item.key}:${records[item.key].wakeAt}`).join('|')
  if (signature && signature !== visibleSignature) {
    collapsed = false
    playChime()
  }
  visibleSignature = signature
  if (before !== JSON.stringify(records)) persist()
  maybeOpenReminder()
}
export function maybeOpenReminder() {
  if (!reminderState.pending.length) { reminderState.open = false; return }
  if (collapsed || document.hidden || reminderState.settingsOpen || reminderState.testOpen) return
  const occupied = document.querySelector('dialog[open]:not(.global-reminder-dialog)') ||
    document.querySelector('.drag-active')
  const typing = document.activeElement?.matches('input:not([type="checkbox"]),textarea,[contenteditable="true"]')
  if (!occupied && !typing) reminderState.open = true
}
export function collapseReminder() {
  collapsed = true
  reminderState.open = false
  reminderState.testOpen = false
}
export function openReminderCenter() {
  reminderState.notice = ''
  reminderState.settingsOpen = true
  reminderState.open = false
  void checkReminders(true)
}
export function expandReminder() {
  collapsed = false
  reminderState.open = reminderState.pending.length > 0
}
export async function checkReminders(force = false) {
  if (!reminderState.owner) return
  if (inFlight !== null) { forceRefresh ||= force; return }
  const version = generation
  const owner = reminderState.owner
  inFlight = version
  try {
    const day = dayKey(new Date())
    if (force || loadedDay !== day || Date.now() - loadedAt >= 15000) {
      read()
      const needYesterday = Object.values(records).some(row => row.status !== 'dismissed' &&
        dayKey(new Date(row.dueAt)) === shiftDay(day, -1))
      const result = await planRequest<DailyPlan[]>(`/agenda/${day}`)
      const yesterday = needYesterday ? await planRequest<DailyPlan[]>(`/agenda/${shiftDay(day, -1)}`) : []
      if (version !== generation || owner !== reminderState.owner) return
      plans = [...result, ...yesterday]
      loadedDay = day
      loadedAt = Date.now()
      reminderState.checkedAt = loadedAt
      reminderState.error = ''
    }
    await locked(() => {
      if (version !== generation) return
      read()
      syncQueue()
    })
    if (version === generation) await notifyPending(version)
  } catch {
    if (version === generation) reminderState.error = '提醒暂时无法同步，连接恢复后会补回当天未处理的提醒。'
  } finally {
    if (inFlight === version) inFlight = null
    if (forceRefresh && version === generation) { forceRefresh = false; void checkReminders(true) }
  }
}
export async function reminderAction(entries: ReminderOccurrence[], action: 'dismiss' | 'snooze') {
  const version = generation
  await locked(() => {
    if (version !== generation) return
    read()
    records = actOnReminders(records, entries.map(item => item.key), action, Date.now())
    persist()
    syncQueue()
  })
  void closeSystemNotifications()
  if (version === generation) {
    nativeSignature = ''
    void checkReminders()
  }
}
export async function completeReminder(item: ReminderOccurrence) {
  if (reminderState.busyKey) return
  const version = generation
  reminderState.busyKey = item.key
  reminderState.error = ''
  try {
    const path = planPath(item.period, item.planDay)
    const current = await planRequest<DailyPlan>(path)
    if (version !== generation) return
    const next = clonePlan(current)
    const task = next.sections.flatMap(section => section.tasks).find(task => task.id === item.task.id)
    if (task && !task.done) {
      task.done = true
      await planRequest<DailyPlan>(path, { method: 'PUT', body: JSON.stringify(next) })
    }
    if (version !== generation) return
    await reminderAction([item], 'dismiss')
    window.dispatchEvent(new Event('planner-updated'))
  } catch {
    if (version === generation) reminderState.error = '未能标记完成，请检查连接后重试，提醒已保留。'
  } finally { if (version === generation) reminderState.busyKey = '' }
}
async function workerRegistration() {
  if (!window.isSecureContext || !('serviceWorker' in navigator)) return null
  if (!registration) {
    registration = navigator.serviceWorker.register('/reminder-sw.js', { scope: '/', updateViaCache: 'none' })
      .then(async () => {
        return await Promise.race([
          navigator.serviceWorker.ready,
          new Promise<null>(resolve => setTimeout(() => resolve(null), 8000))
        ])
      }).catch(() => null).then(result => { if (!result) registration = null; return result })
  }
  return registration
}
async function systemNotification(title: string, body: string, href: string, tag: string, owner: string) {
  const bridge = nativeBridge()
  if (bridge) {
    const ok = bridge.scheduleNotification(JSON.stringify({
      title, body, tag, triggerAt: Date.now() + 1500,
      deepLink: new URL(href, location.origin).href, playSound: true, channelId: 'smarttodo_reminders_sound_v1'
    }))
    if (!ok) throw new Error('Native notification rejected')
    return true
  }
  const worker = await workerRegistration()
  if (owner !== reminderState.owner) return false
  if (worker) {
    await worker.showNotification(title, {
      body, tag, icon: '/favicon.ico', requireInteraction: true,
      data: { href, owner }, timestamp: Date.now()
    } as NotificationOptions)
    if (owner !== reminderState.owner) { await closeSystemNotifications(owner); return false }
    return true
  }
  // Desktop fallback; Android normally requires showNotification on a worker.
  const popup = new Notification(title, { body, tag, icon: '/favicon.ico' })
  desktopNotifications.set(popup, owner)
  popup.onclose = () => desktopNotifications.delete(popup)
  popup.onclick = () => {
    window.focus()
    popup.close()
    if (owner === reminderState.owner) window.dispatchEvent(new CustomEvent('reminder-navigate', { detail: href }))
  }
  return true
}
async function notifyPending(version: number) {
  reminderState.permission = permission()
  if (nativeScheduler()) {
    await syncNativeReminders(version)
    return
  }
  if (reminderState.permission !== 'granted' || Date.now() < retrySystemAt) return
  await locked(async () => {
    if (version !== generation) return
    read()
    const pending = reminderState.pending.filter(item => records[item.key]?.status === 'pending' && !records[item.key].notified)
    if (!pending.length) return
    try {
      const first = pending[0]
      const delivered = await systemNotification('SmartTodo · 到点提醒',
        pending.length === 1 ? `${first.task.time}  ${first.task.title}` : `${first.task.title} 等 ${pending.length} 项待办已到时间`,
        reminderHref(first), `smarttodo-reminders:${reminderState.owner}`, reminderState.owner)
      if (!delivered || version !== generation) return
      for (const item of pending) if (records[item.key]) records[item.key].notified = true
      persist()
      reminderState.deliveryError = ''
    } catch {
      if (version !== generation) return
      retrySystemAt = Date.now() + 60000
      reminderState.deliveryError = '系统通知未发送成功，页面提醒仍保留。请检查浏览器和系统的通知权限。'
    }
  })
}
async function syncNativeReminders(version: number) {
  const bridge = nativeScheduler()
  if (!bridge || version !== generation) return
  const owner = reminderState.owner
  const day = dayKey(new Date())
  // Read future daily instances from the server so daily recurrence and period plans agree.
  if (futureDay !== day || Date.now() - futureLoadedAt > 300000) {
    const loaded: DailyPlan[] = []
    for (let offset = 1; offset < 7; offset++) {
      loaded.push(...await planRequest<DailyPlan[]>(`/agenda/${shiftDay(day, offset)}`))
      if (version !== generation) return
    }
    futurePlans = loaded
    futureLoadedAt = Date.now()
    futureDay = day
  }
  if (version !== generation) return
  await locked(() => {
    if (version !== generation) return
    read()
    const now = Date.now()
    const end = new Date(`${shiftDay(day, 7)}T00:00:00`).getTime()
    const items = reminderOccurrences([...futurePlans, ...plans]).filter(item =>
      item.dueAt < end && (item.dueAt > now || records[item.key]?.status === 'pending' || records[item.key]?.status === 'snoozed'))
    let ledger: { owner: string; alarms: NativeAlarm[] } | null = null
    try { ledger = JSON.parse(localStorage.getItem(NATIVE_LEDGER) || 'null') } catch { /* Rebuild from the server. */ }
    // A reserved alarm fires independently of this page. Keep the page popup, avoid a second system alert.
    if (ledger?.owner === owner && Array.isArray(ledger.alarms) && reminderState.permission === 'granted') {
      for (const item of items) {
        const row = records[item.key]
        if (row?.status === 'pending' && ledger.alarms.some(alarm =>
          alarm.tag === nativeTag(owner, item.key) && alarm.triggerAt <= now && alarm.triggerAt >= row.wakeAt)) row.notified = true
      }
    }
    const alarms = nativeAlarmPlan(items, records, owner, now, true, location.origin)
    // Preserve a just-enqueued immediate notification until its trigger time.
    if (ledger?.owner === owner && Array.isArray(ledger.alarms)) {
      for (const alarm of ledger.alarms) {
        if (alarm.triggerAt > now && !alarms.some(row => row.tag === alarm.tag) &&
            items.some(item => alarm.tag === nativeTag(owner, item.key) && records[item.key]?.status === 'pending')) {
          alarms.push(alarm)
        }
      }
    }
    alarms.sort((a, b) => a.triggerAt - b.triggerAt || a.tag.localeCompare(b.tag))
    const signature = JSON.stringify(alarms)
    if (signature !== nativeSignature) {
      if (!bridge.replaceScheduledNotifications!('smarttodo', signature)) {
        reminderState.deliveryError = '安卓后台提醒未能保存，请检查应用通知权限后重试。'
        return
      }
      nativeSignature = signature
      try { localStorage.setItem(NATIVE_LEDGER, JSON.stringify({ owner, alarms })) } catch { reminderState.storageAvailable = false }
      for (const item of items) {
        const row = records[item.key]
        if (reminderState.permission === 'granted' && row?.status === 'pending' &&
          alarms.some(alarm => alarm.tag === nativeTag(owner, item.key))) row.notified = true
      }
    }
    persist()
    reminderState.nativeCount = alarms.length
    reminderState.deliveryError = ''
  })
}
export function openExactAlarmSettings() {
  try {
    if (!nativeBridge()?.openExactAlarmSettings?.()) throw new Error()
    reminderState.notice = '请允许“闹钟和提醒”，然后返回应用。'
  } catch { reminderState.notice = '请在手机设置中为此应用允许“闹钟和提醒”。' }
}
export async function enableSystemReminders() {
  if (reminderState.enabling) return
  const version = generation
  reminderState.enabling = true
  reminderState.notice = ''
  try {
    const bridge = nativeBridge()
    if (bridge) {
      const result = bridge.requestNotificationPermission()
      reminderState.permission = result
      if (result !== 'granted') {
        bridge.openNotificationSettings()
        reminderState.notice = '请允许通知，并打开横幅、声音和锁屏通知，返回后点击“测试提醒”。'
      } else {
        reminderState.notice = '安卓通知已允许，请测试通知栏与横幅提示。'
        nativeSignature = ''
        void checkReminders(true)
      }
      return
    }
    const value = permission()
    if (value === 'unsupported') throw new Error('此浏览器不支持系统通知，页面弹窗仍可使用。')
    if (value === 'denied') throw new Error('通知已被阻止，请在浏览器的网站权限和手机应用权限中允许通知。')
    // Invoke permission directly in the click gesture, before awaiting worker setup.
    const result = value === 'granted' ? value : await Notification.requestPermission()
    if (version !== generation) return
    reminderState.permission = result
    if (result === 'granted') {
      await workerRegistration()
      reminderState.notice = '通知权限已允许。点击“测试提醒”确认这台设备的提示效果。'
      retrySystemAt = 0
      void checkReminders()
    } else reminderState.notice = '系统通知尚未开启，页面弹窗仍会显示。'
  } catch (failure) {
    if (version === generation) reminderState.notice = failure instanceof Error ? failure.message : '无法开启系统通知。'
  } finally { if (version === generation) reminderState.enabling = false }
}
export async function testReminder() {
  if (reminderState.testing) return
  const version = generation
  reminderState.testing = true
  reminderState.settingsOpen = false
  reminderState.testOpen = true
  reminderState.notice = ''
  unlockAudio()
  playChime()
  try {
    reminderState.permission = permission()
    if (reminderState.permission === 'granted') {
      await systemNotification('SmartTodo · 测试提醒', '这是一条测试通知，实际任务会按开始时间提醒。',
        '/index', `smarttodo-test:${reminderState.owner}`, reminderState.owner)
      if (version === generation) reminderState.notice = '已向系统发送测试通知，请同时检查通知栏。'
    } else reminderState.notice = '页面弹窗测试成功；系统通知需要单独允许权限。'
  } catch {
    if (version === generation) reminderState.notice = '页面弹窗正常；系统通知未发送成功，请检查通知权限。'
  } finally { if (version === generation) reminderState.testing = false }
}
export function setReminderSound(enabled: boolean) {
  reminderState.sound = enabled
  try { localStorage.setItem(`${reminderStorageKey(reminderState.owner)}:sound`, String(enabled)) } catch { /* Session preference still works. */ }
  if (enabled) { unlockAudio(); playChime() }
}
function unlockAudio() {
  if (!reminderState.owner || !reminderState.sound) return
  try {
    audio ||= new AudioContext()
    if (audio.state === 'suspended') void audio.resume().catch(() => {})
  } catch { /* Audio is optional; never block the dialog. */ }
}
function playChime() {
  if (!reminderState.sound || document.hidden || !audio || audio.state !== 'running') return
  for (const [offset, frequency] of [[0, 660], [.2, 880]]) {
    const oscillator = audio.createOscillator()
    const gain = audio.createGain()
    const start = audio.currentTime + offset
    oscillator.frequency.value = frequency
    gain.gain.setValueAtTime(0, start)
    gain.gain.linearRampToValueAtTime(.08, start + .015)
    gain.gain.exponentialRampToValueAtTime(.001, start + .3)
    oscillator.connect(gain)
    gain.connect(audio.destination)
    oscillator.start(start)
    oscillator.stop(start + .32)
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect() }
  }
}
async function closeSystemNotifications(owner = reminderState.owner) {
  for (const [popup, account] of desktopNotifications) if (account === owner) {
    popup.close()
    desktopNotifications.delete(popup)
  }
  try {
    const worker = await navigator.serviceWorker?.getRegistration('/')
    const notifications = await worker?.getNotifications()
    for (const item of notifications || []) if (item.data?.owner === owner) item.close()
  } catch { /* Closing a system notification is best-effort. */ }
}
function refresh() { futureLoadedAt = 0; nativeSignature = ''; void checkReminders(true) }
function visibility() {
  reminderState.permission = permission()
  if (!document.hidden) refresh()
}
function storageChanged(event: StorageEvent) {
  if (event.key === reminderStorageKey(reminderState.owner)) void checkReminders()
}
function workerMessage(event: MessageEvent) {
  if (event.data?.type !== 'smarttodo-reminder-open' || event.data.owner !== reminderState.owner) return
  const href = event.data.href
  if (typeof href === 'string' && /^\/index(?:\?|$)/.test(href)) {
    window.dispatchEvent(new CustomEvent('reminder-navigate', { detail: href }))
  }
}
export function startReminders() {
  if (stopAuthWatch) return
  stopAuthWatch = watch(() => [auth.ready, auth.localMode, auth.user?.username], () => {
    if (!auth.ready) return
    const owner = auth.user ? `${auth.localMode ? 'local' : 'account'}:${auth.user.username}` : ''
    const previous = reminderState.owner
    ++generation
    if (previous) void closeSystemNotifications(previous)
    records = {}
    plans = []
    loadedAt = 0
    loadedDay = ''
    inFlight = null
    forceRefresh = false
    retrySystemAt = 0
    collapsed = false
    visibleSignature = ''
    futurePlans = []
    futureLoadedAt = 0
    futureDay = ''
    nativeSignature = ''
    Object.assign(reminderState, { owner, pending: [], snoozed: [], next: null, open: false, testOpen: false,
      settingsOpen: false, testing: false, enabling: false, error: '', deliveryError: '', notice: '', checkedAt: 0, busyKey: '', nativeCount: 0 })
    try {
      const ledger = JSON.parse(localStorage.getItem(NATIVE_LEDGER) || 'null')
      if (!owner || (ledger && ledger.owner !== owner)) {
        if (nativeScheduler()?.replaceScheduledNotifications?.('smarttodo', '[]')) {
          nativeBridge()?.cancelAllNotifications?.()
          localStorage.removeItem(NATIVE_LEDGER)
        }
      }
    } catch { reminderState.deliveryError = '旧账号的安卓提醒未能清理，请重新打开应用检查。' }
    if (!owner) return
    read()
    try { reminderState.sound = localStorage.getItem(`${reminderStorageKey(owner)}:sound`) !== 'false' } catch { reminderState.sound = true }
    reminderState.permission = permission()
    void workerRegistration()
    refresh()
  }, { immediate: true })
  timer = setInterval(() => { void checkReminders(); maybeOpenReminder() }, 5000)
  document.addEventListener('visibilitychange', visibility)
  window.addEventListener('focus', visibility)
  window.addEventListener('online', refresh)
  window.addEventListener('planner-updated', refresh)
  window.addEventListener('storage', storageChanged)
  window.addEventListener('pointerdown', unlockAudio)
  window.addEventListener('keydown', unlockAudio)
  navigator.serviceWorker?.addEventListener('message', workerMessage)
}
export function stopReminders() {
  ++generation
  stopAuthWatch?.()
  stopAuthWatch = undefined
  clearInterval(timer)
  document.removeEventListener('visibilitychange', visibility)
  window.removeEventListener('focus', visibility)
  window.removeEventListener('online', refresh)
  window.removeEventListener('planner-updated', refresh)
  window.removeEventListener('storage', storageChanged)
  window.removeEventListener('pointerdown', unlockAudio)
  window.removeEventListener('keydown', unlockAudio)
  navigator.serviceWorker?.removeEventListener('message', workerMessage)
  if (audio) void audio.close().catch(() => {})
  audio = null
}
