import { dayKey, timeMinutes, validDay, type DailyPlan, type PlanPeriod, type PlannerReminder } from './planner'

export interface ReminderOccurrence extends PlannerReminder {
  key: string
  day: string
  dueAt: number
  period: PlanPeriod
  planDay: string
}
export interface ReminderRecord {
  dueAt: number
  status: 'pending' | 'snoozed' | 'dismissed'
  wakeAt: number
  notified: boolean
}
export type ReminderRecords = Record<string, ReminderRecord>
const WEEK = 7 * 86400000

export function reminderStorageKey(owner: string) {
  return `smarttodo-reminders-v2:${encodeURIComponent(owner)}`
}
export function readReminderRecords(value: string | null, now: number): ReminderRecords {
  const result: ReminderRecords = {}
  try {
    const parsed = JSON.parse(value || '{}')
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') return result
    for (const [key, entry] of Object.entries(parsed).slice(-6000)) {
      const row = entry as ReminderRecord
      if (key.length > 400 || !row || !Number.isFinite(row.dueAt) || !Number.isFinite(row.wakeAt) ||
          row.dueAt < now - WEEK || row.dueAt > now + 86400000 ||
          !['pending', 'snoozed', 'dismissed'].includes(row.status)) continue
      result[key] = { dueAt: row.dueAt, wakeAt: row.wakeAt, status: row.status, notified: row.notified === true }
    }
  } catch { /* A corrupt or unavailable browser store must not disable reminders. */ }
  return result
}
export function reminderOccurrences(plans: DailyPlan[]): ReminderOccurrence[] {
  const results = new Map<string, ReminderOccurrence>()
  for (const plan of plans) {
    const period = plan.period || 'day'
    for (const section of plan.sections) {
      for (const task of section.tasks) {
        const day = period === 'day' ? plan.day : task.scheduledDate
        const minutes = timeMinutes(task.time)
        if (task.done || !validDay(day) || minutes === null) continue
        const date = new Date(`${day}T00:00:00`)
        date.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0)
        const key = JSON.stringify([period, plan.day, day, task.id, task.time])
        results.set(key, {
          key, day, dueAt: date.getTime(), period, planDay: plan.day,
          sectionId: section.id, sectionTitle: section.title, task: { ...task }
        })
      }
    }
  }
  return [...results.values()].sort((a, b) => a.dueAt - b.dueAt || a.key.localeCompare(b.key))
}
export function reconcileReminders(occurrences: ReminderOccurrence[], previous: ReminderRecords, now: number) {
  const records = readReminderRecords(JSON.stringify(previous), now)
  const available = new Map(occurrences.map(item => [item.key, item]))
  const today = dayKey(new Date(now))
  for (const [key, row] of Object.entries(records)) {
    if (row.status !== 'dismissed' && (!available.has(key) || row.dueAt < now - 86400000)) delete records[key]
  }
  for (const item of occurrences) {
    if (item.dueAt > now || (item.day !== today && !records[item.key])) continue
    const existing = records[item.key]
    if (!existing) records[item.key] = { dueAt: item.dueAt, wakeAt: item.dueAt, status: 'pending', notified: false }
    else if (existing.status === 'snoozed' && existing.wakeAt <= now) {
      records[item.key] = { ...existing, status: 'pending', notified: false }
    }
  }
  const pending = occurrences.filter(item => records[item.key]?.status === 'pending' && item.dueAt <= now)
  const snoozed = occurrences.filter(item => records[item.key]?.status === 'snoozed')
  return { records, pending, snoozed }
}
export function actOnReminders(records: ReminderRecords, keys: string[], action: 'dismiss' | 'snooze', now: number) {
  const next = { ...records }
  for (const key of keys) {
    if (!next[key]) continue
    next[key] = { ...next[key], status: action === 'snooze' ? 'snoozed' : 'dismissed',
      wakeAt: action === 'snooze' ? now + 5 * 60000 : next[key].wakeAt, notified: false }
  }
  return next
}
export function reminderHref(item: ReminderOccurrence) {
  return `/index?${new URLSearchParams({ date: item.day, period: item.period, task: item.task.id })}`
}
