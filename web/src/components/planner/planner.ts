import { apiFetch } from '../../http'

export type PlanColor = 'rose' | 'gold' | 'sage' | 'blue' | 'lilac' | 'teal'
export type PlanPeriod = 'day' | 'week' | 'month' | 'year'
export interface PlanTask {
  id: string
  title: string
  notes: string
  kind: 'task' | 'event'
  time: string
  endTime?: string
  scheduledDate?: string
  done: boolean
  daily?: boolean
}
export interface PlanSection {
  id: string
  title: string
  color: PlanColor
  start: string
  end: string
  tasks: PlanTask[]
}
export interface DailyPlan {
  period?: PlanPeriod
  endDay?: string
  day: string
  revision: number
  schedule_revision: number
  title: string
  sections: PlanSection[]
}
export interface DayCounts { total: number; done: number }
export interface PlannerReminder {
  period?: PlanPeriod
  planDay?: string
  sectionId: string
  sectionTitle: string
  task: PlanTask
}

export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function validDay(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(`${value}T12:00:00`)
  return !Number.isNaN(date.getTime()) && dayKey(date) === value
}

export function shiftDay(day: string, offset: number): string {
  const date = new Date(`${day}T12:00:00`)
  date.setDate(date.getDate() + offset)
  return dayKey(date)
}

export function weekDays(day: string): string[] {
  const weekday = new Date(`${day}T12:00:00`).getDay()
  const monday = shiftDay(day, -((weekday + 6) % 7))
  return Array.from({ length: 7 }, (_, index) => shiftDay(monday, index))
}

export function validPeriod(value: unknown): value is PlanPeriod {
  return typeof value === 'string' && ['day', 'week', 'month', 'year'].includes(value)
}

export function periodBounds(period: PlanPeriod, day: string): { start: string; end: string } {
  if (period === 'week') {
    const days = weekDays(day)
    return { start: days[0], end: days[6] }
  }
  if (period === 'month') {
    const date = new Date(`${day}T12:00:00`)
    date.setMonth(date.getMonth() + 1, 0)
    return { start: `${day.slice(0, 7)}-01`, end: dayKey(date) }
  }
  if (period === 'year') return { start: `${day.slice(0, 4)}-01-01`, end: `${day.slice(0, 4)}-12-31` }
  return { start: day, end: day }
}

export function shiftPeriod(period: PlanPeriod, day: string, offset: number): string {
  if (period === 'day' || period === 'week') return shiftDay(day, offset * (period === 'week' ? 7 : 1))
  const date = new Date(`${day}T12:00:00`)
  date.setDate(1)
  if (period === 'month') date.setMonth(date.getMonth() + offset)
  else date.setFullYear(date.getFullYear() + offset, 0, 1)
  return dayKey(date)
}

export function planPath(period: PlanPeriod, day: string): string {
  return period === 'day' ? `/day/${day}` : `/period/${period}/${periodBounds(period, day).start}`
}

export function samePlan(left: DailyPlan, right: DailyPlan): boolean {
  return left.day === right.day && (left.period || 'day') === (right.period || 'day')
}

export function clonePlan(plan: DailyPlan): DailyPlan {
  return JSON.parse(JSON.stringify(plan))
}

export function planCounts(plan: DailyPlan): DayCounts {
  const tasks = plan.sections.flatMap(section => section.tasks)
  return { total: tasks.length, done: tasks.filter(task => task.done).length }
}

export function taskTimeLabel(task: Pick<PlanTask, 'time' | 'endTime'>): string {
  if (!task.time) return '\u5168\u5929'
  return task.endTime ? `${task.time}\uFF5E${task.endTime}` : task.time
}

export interface ScheduleEntry {
  task: PlanTask
  section: PlanSection
  date: string
}
export interface SchedulePlacement extends ScheduleEntry {
  start: number
  end: number
  lane: number
  lanes: number
}

export function scheduleEntries(plan: DailyPlan, sectionId = '', todoOnly = false): ScheduleEntry[] {
  return plan.sections.filter(section => !sectionId || section.id === sectionId)
    .flatMap(section => section.tasks.filter(task => !todoOnly || !task.done)
      .map(task => ({ task, section, date: !plan.period || plan.period === 'day' ? plan.day : task.scheduledDate || '' })))
    .sort((a, b) => (a.date || '9999').localeCompare(b.date || '9999') ||
      a.task.time.localeCompare(b.task.time))
}

export function timeMinutes(time: string): number | null {
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) return null
  const [hour, minute] = time.split(':').map(Number)
  return hour * 60 + minute
}

export function monthCells(day: string): string[] {
  const { start, end } = periodBounds('month', day)
  const first = weekDays(start)[0]
  const last = weekDays(end)[6]
  const cells: string[] = []
  for (let current = first; current <= last; current = shiftDay(current, 1)) cells.push(current)
  return cells
}

export function scheduleLayout(entries: ScheduleEntry[], minimumMinutes = 30): SchedulePlacement[] {
  const positioned: SchedulePlacement[] = entries.flatMap(entry => {
    const start = timeMinutes(entry.task.time)
    if (start === null) return []
    const end = timeMinutes(entry.task.endTime || '')
    return [{ ...entry, start, end: Math.max(end || start, start + minimumMinutes), lane: 0, lanes: 1 }]
  }).sort((a, b) => a.start - b.start || b.end - a.end)
  let group: SchedulePlacement[] = []
  let ends: number[] = []
  let groupEnd = -1
  function finishGroup() {
    for (const placement of group) placement.lanes = ends.length
    group = []
    ends = []
  }
  // Include the minimum hit-target height when assigning lanes to short events.
  for (const placement of positioned) {
    if (placement.start >= groupEnd) finishGroup()
    let lane = ends.findIndex(end => end <= placement.start)
    if (lane < 0) lane = ends.length
    ends[lane] = placement.end
    placement.lane = lane
    group.push(placement)
    groupEnd = Math.max(groupEnd, placement.end)
  }
  finishGroup()
  return positioned
}

function taskDueAt(day: string, time: string): Date | null {
  const match = /^(\d{2}):(\d{2})$/.exec(time)
  if (!match) return null
  const [year, month, date] = day.split('-').map(Number)
  return new Date(year, month - 1, date, Number(match[1]), Number(match[2]), 0, 0)
}

export function reminderKey(day: string, task: PlanTask, period: PlanPeriod = 'day'): string {
  return `${period === 'day' ? '' : `${period}:`}${day}:${task.id}:${task.time}`
}

export function dueReminderTasks(plan: DailyPlan, from: Date, to: Date): PlannerReminder[] {
  const period = plan.period || 'day'
  if ((period === 'day' && dayKey(to) !== plan.day) || to.getTime() <= from.getTime()) return []
  const reminders: PlannerReminder[] = []
  for (const section of plan.sections) {
    for (const task of section.tasks) {
      if (task.done || !task.time) continue
      const scheduledDay = period === 'day' ? plan.day : task.scheduledDate
      if (!scheduledDay || scheduledDay !== dayKey(to)) continue
      const dueAt = taskDueAt(scheduledDay, task.time)
      if (dueAt && dueAt.getTime() > from.getTime() && dueAt.getTime() <= to.getTime()) {
        reminders.push({
          sectionId: section.id, sectionTitle: section.title, task: { ...task },
          ...(period !== 'day' ? { period, planDay: plan.day } : {})
        })
      }
    }
  }
  return reminders
}

export function moveTask(plan: DailyPlan, taskId: string, sectionId: string, beforeId: string | null): DailyPlan {
  const next = clonePlan(plan)
  const source = next.sections.find(section => section.tasks.some(task => task.id === taskId))
  const target = next.sections.find(section => section.id === sectionId)
  if (!source || !target || taskId === beforeId) return next
  if (beforeId !== null && !target.tasks.some(task => task.id === beforeId)) return next
  const index = source.tasks.findIndex(task => task.id === taskId)
  const [task] = source.tasks.splice(index, 1)
  const destination = beforeId === null ? target.tasks.length : target.tasks.findIndex(task => task.id === beforeId)
  target.tasks.splice(destination, 0, task)
  return next
}

export function moveTaskBy(plan: DailyPlan, taskId: string, delta: number): DailyPlan {
  const next = clonePlan(plan)
  const section = next.sections.find(section => section.tasks.some(task => task.id === taskId))
  if (!section) return next
  const index = section.tasks.findIndex(task => task.id === taskId)
  const destination = index + delta
  if (destination < 0 || destination >= section.tasks.length) return next
  const [task] = section.tasks.splice(index, 1)
  section.tasks.splice(destination, 0, task)
  return next
}

export function dropBeforeTask(
  rows: { id: string; top: number; height: number }[], draggedId: string, pointerY: number
): string | null {
  return rows.find(row => row.id !== draggedId && pointerY < row.top + row.height / 2)?.id || null
}

export function dragScrollSpeed(pointerY: number, top: number, bottom: number): number {
  const edge = Math.min(80, (bottom - top) / 3)
  if (edge <= 0) return 0
  if (pointerY < top + edge) return -Math.min(16, Math.ceil((top + edge - pointerY) / edge * 16))
  if (pointerY > bottom - edge) return Math.min(16, Math.ceil((pointerY - bottom + edge) / edge * 16))
  return 0
}

export class PlanRequestError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function planRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api/planner${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    signal: AbortSignal.timeout(12000)
  })
  if (!response.ok) {
    throw new PlanRequestError(response.status, (await response.json().catch(() => ({}))).error || 'Request failed')
  }
  return response.json()
}
