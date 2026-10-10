import { reminderHref, type ReminderOccurrence, type ReminderRecords } from './reminder-state'

interface NativeBridge {
  getScheduledNotificationVersion?: () => number
  replaceScheduledNotifications?: (namespace: string, payload: string) => boolean
  getNotificationPermissionState: () => NotificationPermission
  requestNotificationPermission: () => NotificationPermission
  openNotificationSettings: () => boolean
  openExactAlarmSettings?: () => boolean
  canScheduleExactAlarms: () => boolean
  scheduleNotification: (payload: string) => boolean
  cancelAllNotifications?: () => boolean
}
export interface NativeAlarm {
  tag: string; title: string; body: string; triggerAt: number; deepLink: string
  channelId: string; playSound: boolean
}
export function nativeBridge(): NativeBridge | null {
  const bridge = (window as Window & { NativeBridge?: NativeBridge }).NativeBridge
  return bridge && typeof bridge.getNotificationPermissionState === 'function' ? bridge : null
}
export function nativeScheduler(): NativeBridge | null {
  const bridge = nativeBridge()
  try {
    return bridge?.getScheduledNotificationVersion?.() === 1 &&
      typeof bridge.replaceScheduledNotifications === 'function' ? bridge : null
  } catch { return null }
}
export function nativeTag(owner: string, key: string) {
  // Keep the occurrence identity intact; Android assigns a stable PendingIntent per tag.
  return `smarttodo:${owner}:${key}`
}
export function nativeAlarmPlan(
  items: ReminderOccurrence[], records: ReminderRecords, owner: string, now: number, sound: boolean, origin: string
) {
  const alarms: NativeAlarm[] = []
  for (const item of items) {
    const record = records[item.key]
    if (record?.status === 'dismissed') continue
    const triggerAt = record?.status === 'snoozed' ? record.wakeAt : item.dueAt
    if (triggerAt <= now && record?.notified) continue
    alarms.push({
      tag: nativeTag(owner, item.key), title: 'SmartTodo · 到点提醒',
      body: `${item.task.time}${item.task.endTime ? `–${item.task.endTime}` : ''}  ${item.task.title}`,
      triggerAt: triggerAt <= now ? now + 1500 : triggerAt,
      deepLink: new URL(reminderHref(item), origin).href,
      channelId: sound ? 'smarttodo_reminders_sound_v1' : 'smarttodo_reminders_silent_v1', playSound: sound
    })
  }
  return alarms.sort((a, b) => a.triggerAt - b.triggerAt).slice(0, 500)
}
