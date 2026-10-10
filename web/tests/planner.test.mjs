import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sourceUrl } from './load-source.mjs'
const {
  moveTask, moveTaskBy, weekDays, shiftDay, validDay, planCounts, dropBeforeTask, dragScrollSpeed,
  dueReminderTasks, reminderKey, taskTimeLabel, validPeriod, periodBounds, shiftPeriod, planPath, samePlan,
  scheduleEntries, scheduleLayout, monthCells, timeMinutes
} =
  await import(sourceUrl('../src/components/planner/planner.ts'))

const board = () => ({
  day: '2026-10-08', revision: 0, title: 'Plan',
  sections: [
    { id: 'one', tasks: [{ id: 'a', done: false }, { id: 'b', done: true }, { id: 'c', done: false }] },
    { id: 'two', tasks: [{ id: 'd', done: false }] },
    { id: 'empty', tasks: [] }
  ]
})
const ids = section => section.tasks.map(task => task.id)

test('schedule entries preserve every task, period dates, filtering and source data', () => {
  const original = board()
  Object.assign(original.sections[0].tasks[0], { time: '09:50', endTime: '11:00', scheduledDate: '2026-10-09' })
  Object.assign(original.sections[0].tasks[1], { time: '' })
  Object.assign(original.sections[0].tasks[2], { time: '08:00', scheduledDate: '2026-10-08' })
  original.sections[1].tasks[0].time = ''
  const before = JSON.stringify(original)
  assert.equal(scheduleEntries(original).length, 4)
  assert.ok(scheduleEntries(original).every(entry => entry.date === original.day))
  assert.deepEqual(scheduleEntries({ ...original, period: 'week' }, 'one', true).map(entry => [entry.task.id, entry.date]),
    [['c', '2026-10-08'], ['a', '2026-10-09']])
  assert.equal(scheduleEntries({ ...original, period: 'year' }).filter(entry => !entry.date).length, 2)
  assert.equal(scheduleEntries(original, 'missing').length, 0)
  assert.equal(JSON.stringify(original), before)
})

test('month calendar starts on Monday and includes all dates including leap days', () => {
  const october = monthCells('2026-10-09')
  assert.equal(october[0], '2026-09-28')
  assert.equal(october.at(-1), '2026-11-01')
  assert.equal(october.length, 35)
  assert.equal(new Set(october).size, october.length)
  assert.ok(monthCells('2024-02-01').includes('2024-02-29'))
  assert.ok(!monthCells('2026-02-01').includes('2026-02-29'))
  assert.equal(monthCells('2026-03-01').length, 42)
})

const scheduleEntry = (id, time, endTime = '') => ({ date: '2026-10-09', section: { id: 's' }, task: { id, time, endTime } })
test('time grid uses separate lanes for simultaneous and chained overlapping tasks', () => {
  const entries = [scheduleEntry('a', '09:00', '11:00'), scheduleEntry('b', '09:30', '10:00'),
    scheduleEntry('c', '10:00', '11:30'), scheduleEntry('d', '12:00', '13:00')]
  const before = JSON.stringify(entries)
  const positions = scheduleLayout(entries)
  assert.deepEqual(positions.map(item => [item.task.id, item.lane, item.lanes]), [['a', 0, 2], ['b', 1, 2], ['c', 1, 2], ['d', 0, 1]])
  assert.equal(JSON.stringify(entries), before)
  for (const first of positions) for (const second of positions) {
    if (first === second || first.lane !== second.lane) continue
    assert.ok(first.end <= second.start || second.end <= first.start)
  }
})

test('short tasks, single times and midnight keep usable hit areas without inventing end times', () => {
  const positions = scheduleLayout([scheduleEntry('a', '09:00', '09:01'), scheduleEntry('b', '09:10'),
    scheduleEntry('c', '23:59'), scheduleEntry('d', '00:00'), scheduleEntry('all', '')])
  assert.equal(positions.length, 4)
  assert.equal(positions.find(item => item.task.id === 'a').end, 570)
  assert.equal(positions.find(item => item.task.id === 'b').lanes, 2)
  assert.equal(positions.find(item => item.task.id === 'c').start, 1439)
  assert.equal(positions.find(item => item.task.id === 'c').task.endTime, '')
  assert.equal(positions[0].start, 0)
  assert.equal(timeMinutes('09:50'), 590)
  for (const invalid of ['', '24:00', '9:00', '12:60', 'oops']) assert.equal(timeMinutes(invalid), null)
})

test('dragging within a section preserves exact insertion order', () => {
  const original = board()
  const moved = moveTask(original, 'c', 'one', 'a')
  assert.deepEqual(ids(moved.sections[0]), ['c', 'a', 'b'])
  assert.deepEqual(ids(original.sections[0]), ['a', 'b', 'c'])
  assert.deepEqual(ids(moveTask(original, 'a', 'one', null).sections[0]), ['b', 'c', 'a'])
})

test('dragging across sections and into an empty section preserves tasks', () => {
  const moved = moveTask(board(), 'a', 'two', 'd')
  assert.deepEqual(ids(moved.sections[0]), ['b', 'c'])
  assert.deepEqual(ids(moved.sections[1]), ['a', 'd'])
  assert.equal(moveTask(board(), 'a', 'empty', null).sections[2].tasks[0].id, 'a')
  assert.deepEqual(planCounts(moved), { total: 4, done: 1 })
})

test('invalid targets and self drops do not delete tasks', () => {
  for (const args of [['a', 'missing', null], ['a', 'two', 'missing'], ['a', 'one', 'a'], ['missing', 'two', null]]) {
    assert.deepEqual(moveTask(board(), ...args), board())
  }
})

test('button movement matches manual priority ordering and respects boundaries', () => {
  assert.deepEqual(ids(moveTaskBy(board(), 'b', -1).sections[0]), ['b', 'a', 'c'])
  assert.deepEqual(ids(moveTaskBy(board(), 'b', 1).sections[0]), ['a', 'c', 'b'])
  assert.deepEqual(moveTaskBy(board(), 'a', -1), board())
  assert.deepEqual(moveTaskBy(board(), 'c', 1), board())
})

test('calendar respects weeks, leap years and month boundaries', () => {
  assert.deepEqual(weekDays('2026-10-08'), ['2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09', '2026-10-10', '2026-10-11'])
  assert.equal(shiftDay('2026-12-31', 1), '2027-01-01')
  assert.equal(shiftDay('2024-02-28', 1), '2024-02-29')
  assert.equal(validDay('2026-02-30'), false)
  assert.equal(validDay('2026-10-08'), true)
})

test('daily repeat settings and schedule revision survive dragging and reordering', () => {
  const original = board()
  original.schedule_revision = 7
  Object.assign(original.sections[0].tasks[0], { daily: true, notes: 'Every morning', time: '08:30', endTime: '09:50' })
  const moved = moveTask(original, 'a', 'two', null)
  assert.deepEqual(moved.sections[1].tasks[1], original.sections[0].tasks[0])
  assert.equal(moved.schedule_revision, 7)
  assert.equal(moveTaskBy(moved, 'a', -1).sections[1].tasks[0].daily, true)
  assert.equal(original.sections[0].tasks[0].daily, true)
  assert.deepEqual(planCounts(moved), { total: 4, done: 1 })
})

test('drop positions skip the dragged row and use visible row midpoints', () => {
  const rows = [{ id: 'a', top: 100, height: 60 }, { id: 'b', top: 160, height: 100 }, { id: 'c', top: 260, height: 60 }]
  assert.equal(dropBeforeTask(rows, 'a', 100), 'b')
  assert.equal(dropBeforeTask(rows, 'a', 211), 'c')
  assert.equal(dropBeforeTask(rows, 'c', 129), 'a')
  assert.equal(dropBeforeTask(rows, 'a', 300), null)
  assert.equal(dropBeforeTask([], 'a', 300), null)
  assert.equal(dropBeforeTask([rows[0]], 'a', 100), null)
  const filtered = rows.filter(row => row.id !== 'b')
  assert.equal(dropBeforeTask(filtered, 'a', 170), 'c')
})

test('edge scrolling accelerates near the edge and respects bottom navigation', () => {
  assert.equal(dragScrollSpeed(400, 0, 800), 0)
  assert.equal(dragScrollSpeed(0, 0, 800), -16)
  assert.equal(dragScrollSpeed(800, 0, 800), 16)
  assert.equal(dragScrollSpeed(760, 0, 800), 8)
  assert.equal(dragScrollSpeed(760, 0, 740), 16)
  assert.equal(dragScrollSpeed(-100, 0, 800), -16)
  assert.equal(dragScrollSpeed(0, 0, 0), 0)
})

test('reminders trigger only for unfinished tasks crossing their local due minute', () => {
  const plan = {
    day: '2026-10-08', revision: 1, schedule_revision: 1, title: 'Plan',
    sections: [
      { id: 'one', title: 'Morning', color: 'rose', start: '', end: '', tasks: [
        { id: 'a', title: 'Start', kind: 'task', time: '10:00', done: false },
        { id: 'b', title: 'Done', kind: 'task', time: '10:00', done: true },
        { id: 'c', title: 'Later', kind: 'task', time: '10:01', done: false },
        { id: 'd', title: 'All day', kind: 'task', time: '', done: false }
      ] }
    ]
  }
  const from = new Date(2026, 9, 8, 9, 59, 50)
  const to = new Date(2026, 9, 8, 10, 0, 15)
  const reminders = dueReminderTasks(plan, from, to)
  assert.deepEqual(reminders.map(item => item.task.id), ['a'])
  assert.equal(reminderKey(plan.day, reminders[0].task), '2026-10-08:a:10:00')
  assert.deepEqual(dueReminderTasks(plan, to, new Date(2026, 9, 8, 10, 0, 30)), [])
  assert.deepEqual(dueReminderTasks(plan, new Date(2026, 9, 8, 10, 0, 30), new Date(2026, 9, 8, 10, 1, 1)).map(item => item.task.id), ['c'])
  assert.deepEqual(dueReminderTasks(plan, new Date(2026, 9, 9, 9, 59), new Date(2026, 9, 9, 10, 1)), [])
})

test('task time labels support ranges, legacy single times and all-day tasks', () => {
  assert.equal(taskTimeLabel({ time: '09:50', endTime: '11:00' }), '09:50\uFF5E11:00')
  assert.equal(taskTimeLabel({ time: '09:50' }), '09:50')
  assert.equal(taskTimeLabel({ time: '09:50', endTime: '' }), '09:50')
  assert.equal(taskTimeLabel({ time: '' }), '\u5168\u5929')
  assert.equal(taskTimeLabel({ time: '', endTime: '' }), '\u5168\u5929')
})

test('range reminders trigger at the start only and retain the full range', () => {
  const plan = board()
  plan.sections[0].tasks = [
    { id: 'a', time: '09:50', endTime: '11:00', daily: true, done: false }
  ]
  const entries = dueReminderTasks(plan, new Date(2026, 9, 8, 9, 49, 59), new Date(2026, 9, 8, 9, 50))
  assert.equal(entries.length, 1)
  assert.equal(entries[0].task.endTime, '11:00')
  assert.deepEqual(dueReminderTasks(plan, new Date(2026, 9, 8, 10, 59, 59), new Date(2026, 9, 8, 11)), [])
  const task = entries[0].task
  assert.equal(reminderKey(plan.day, task), reminderKey(plan.day, { ...task, endTime: '12:00' }))
})

test('period bounds are normalized across weeks, leap months and year boundaries', () => {
  assert.deepEqual(periodBounds('week', '2027-01-01'), { start: '2026-12-28', end: '2027-01-03' })
  assert.deepEqual(periodBounds('month', '2024-02-20'), { start: '2024-02-01', end: '2024-02-29' })
  assert.deepEqual(periodBounds('month', '2026-02-20'), { start: '2026-02-01', end: '2026-02-28' })
  assert.deepEqual(periodBounds('year', '2026-10-09'), { start: '2026-01-01', end: '2026-12-31' })
  assert.deepEqual(periodBounds('day', '2026-10-09'), { start: '2026-10-09', end: '2026-10-09' })
  assert.equal(shiftPeriod('week', '2026-12-28', 1), '2027-01-04')
  assert.equal(shiftPeriod('month', '2026-01-31', 1), '2026-02-01')
  assert.equal(shiftPeriod('month', '2026-01-31', -1), '2025-12-01')
  assert.equal(shiftPeriod('year', '2024-02-29', 1), '2025-01-01')
  assert.equal(validPeriod('year'), true)
  assert.equal(validPeriod('decade'), false)
})

test('period plan paths and identities keep daily storage separate', () => {
  assert.equal(planPath('day', '2026-10-09'), '/day/2026-10-09')
  assert.equal(planPath('week', '2026-10-09'), '/period/week/2026-10-05')
  assert.equal(planPath('month', '2026-10-09'), '/period/month/2026-10-01')
  assert.equal(samePlan({ day: '2026-10-01' }, { day: '2026-10-01', period: 'day' }), true)
  assert.equal(samePlan({ day: '2026-10-01' }, { day: '2026-10-01', period: 'month' }), false)
})

test('period reminders use the execution date and independent notification keys', () => {
  const plan = board()
  plan.day = '2026-10-01'
  plan.period = 'month'
  plan.sections[0].tasks = [
    { id: 'a', time: '09:50', scheduledDate: '2026-10-09', done: false },
    { id: 'b', time: '09:50', scheduledDate: '2026-10-08', done: false },
    { id: 'c', time: '', scheduledDate: '', done: false },
    { id: 'e', time: '09:50', scheduledDate: '2026-10-09', done: true },
  ]
  const entries = dueReminderTasks(plan, new Date(2026, 9, 9, 9, 49, 59), new Date(2026, 9, 9, 9, 50))
  assert.deepEqual(entries.map(entry => entry.task.id), ['a'])
  assert.equal(entries[0].period, 'month')
  assert.equal(entries[0].planDay, '2026-10-01')
  assert.notEqual(reminderKey('2026-10-09', entries[0].task), reminderKey('2026-10-09', entries[0].task, 'month'))
  assert.equal(moveTask(plan, 'a', 'two', null).sections[1].tasks[1].scheduledDate, '2026-10-09')
})
