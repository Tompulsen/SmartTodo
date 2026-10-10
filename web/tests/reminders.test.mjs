import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sourceUrl } from './load-source.mjs'
const { reminderOccurrences, reconcileReminders, actOnReminders, readReminderRecords, reminderStorageKey, reminderHref } =
  await import(sourceUrl('../src/components/planner/reminder-state.ts'))
const { nativeAlarmPlan } = await import(sourceUrl('../src/components/planner/native-reminders.ts'))
const now = new Date('2026-10-10T10:00:00').getTime()
const plan = (period = 'day', tasks = []) => ({
  day: '2026-10-10', period, sections: [{ id: 's1', title: 'Morning', tasks }], revision: 0
})
const task = (id = 'a', extra = {}) => ({
  id, title: 'Focus', time: '09:50', endTime: '11:00', done: false, kind: 'task', ...extra
})
const due = () => reminderOccurrences([plan('day', [task()])])

test('late opening catches up today, including period tasks; completed and untimed tasks are excluded', () => {
  const items = reminderOccurrences([
    plan('day', [task(), task('done', { done: true }), task('no-time', { time: '' })]),
    plan('week', [task('weekly', { scheduledDate: '2026-10-10' }), task('unscheduled')]),
    plan('month', [task('monthly', { scheduledDate: '2026-10-10' })]),
    plan('year', [task('yearly', { scheduledDate: '2026-10-11' })])
  ])
  const result = reconcileReminders(items, {}, now)
  assert.deepEqual(result.pending.map(row => row.task.id), ['a', 'monthly', 'weekly'])
  assert.ok(result.pending.every(row => row.dueAt === new Date('2026-10-10T09:50:00').getTime()))
  assert.equal(items.find(row => row.task.id === 'a').task.endTime, '11:00')
})
test('pending survives reload, acknowledgement does not complete tasks, and owners have separate keys', () => {
  const items = due()
  const first = reconcileReminders(items, {}, now)
  assert.equal(reconcileReminders(items, readReminderRecords(JSON.stringify(first.records), now), now).pending.length, 1)
  const dismissed = actOnReminders(first.records, [items[0].key], 'dismiss', now)
  assert.equal(reconcileReminders(items, dismissed, now + 1000).pending.length, 0)
  assert.equal(items[0].task.done, false)
  assert.notEqual(reminderStorageKey('account:a'), reminderStorageKey('account:b'))
})
test('snooze waits five minutes across a reload and midnight, then becomes pending once', () => {
  const items = reminderOccurrences([plan('day', [task('a', { time: '23:59' })])])
  const at = new Date('2026-10-10T23:59:30').getTime()
  const first = reconcileReminders(items, {}, at)
  const snoozed = actOnReminders(first.records, [items[0].key], 'snooze', at)
  assert.equal(reconcileReminders(items, snoozed, at + 299000).pending.length, 0)
  const result = reconcileReminders(items, snoozed, at + 300000)
  assert.equal(result.pending.length, 1)
  assert.equal(result.records[items[0].key].notified, false)
})
test('deleted/completed/moved-in-time tasks remove stale pending and period plan keys do not collide', () => {
  const items = due()
  const records = reconcileReminders(items, {}, now).records
  assert.equal(Object.keys(reconcileReminders([], records, now).records).length, 0)
  const edited = reminderOccurrences([plan('day', [task('a', { time: '11:00' })])])
  assert.equal(reconcileReminders(edited, records, now).pending.length, 0)
  const period = reminderOccurrences([plan('week', [task('a', { scheduledDate: '2026-10-10' })])])
  assert.notEqual(items[0].key, period[0].key)
  assert.equal(reminderOccurrences([plan('day', [task()]), plan('day', [task()])]).length, 1)
  assert.match(reminderHref(period[0]), /period=week/)
})
test('future and old tasks do not cause a historical notification storm; malformed storage is ignored', () => {
  const old = { ...plan('day', [task()]), day: '2026-10-09' }
  const future = { ...plan('day', [task()]), day: '2026-10-11' }
  assert.equal(reconcileReminders(reminderOccurrences([old, future]), {}, now).pending.length, 0)
  for (const raw of ['{broken', 'null', '[]', '{"x":{"dueAt":"wrong"}}']) assert.deepEqual(readReminderRecords(raw, now), {})
})
test('native alarms retain local timestamps and deep links, reflect snooze, and cancel acknowledged tasks', () => {
  const items = due()
  const result = reconcileReminders(items, {}, now)
  const records = actOnReminders(result.records, [items[0].key], 'snooze', now)
  const native = nativeAlarmPlan(items, records, 'account:a', now, true, 'https://todo.example')
  assert.equal(native.length, 1)
  assert.equal(native[0].triggerAt, now + 300000)
  assert.match(native[0].deepLink, /^https:\/\/todo\.example\/index\?/)
  assert.match(native[0].body, /09:50–11:00/)
  assert.equal(native[0].channelId, 'smarttodo_reminders_sound_v1')
  assert.equal(nativeAlarmPlan(items, actOnReminders(records, [items[0].key], 'dismiss', now), 'account:a', now, true, 'https://todo.example').length, 0)
  assert.notEqual(native[0].tag, nativeAlarmPlan(items, records, 'account:b', now, true, 'https://todo.example')[0].tag)
})
