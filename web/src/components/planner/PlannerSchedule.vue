<template>
  <section class="schedule-view" :aria-label="`${periodLabel}计划视图`" :aria-busy="busy">
    <div class="schedule-toolbar">
      <div class="schedule-mode-switch" role="group" aria-label="视图形式">
        <button :class="{ selected: mode === 'calendar' }" :aria-pressed="mode === 'calendar'" @click="mode = 'calendar'"><PlannerIcon name="calendar" />{{ periodLabel }}视图</button>
        <button :class="{ selected: mode === 'table' }" :aria-pressed="mode === 'table'" @click="mode = 'table'"><PlannerIcon name="list" />任务表</button>
      </div>
      <div class="schedule-filter">
        <label><span class="sr-only">宫格分类</span><select v-model="category" aria-label="宫格分类"><option value="">全部分类</option><option v-for="section in plan.sections" :key="section.id" :value="section.id">{{ section.title }}</option></select></label>
        <span class="schedule-total">{{ entries.length }} 项</span>
      </div>
    </div>

    <div v-if="mode === 'table'" class="schedule-table-scroll" role="region" aria-label="任务表格" tabindex="0">
      <table class="schedule-table">
        <caption class="sr-only">{{ plan.title }}的全部筛选任务</caption>
        <thead><tr><th scope="col">状态</th><th scope="col">任务 / 事项</th><th scope="col">宫格分类</th><th scope="col">执行日期</th><th scope="col">时间安排</th><th scope="col">重复</th><th scope="col"><span class="sr-only">操作</span></th></tr></thead>
        <tbody>
          <tr v-for="entry in entries" :key="entry.task.id" :class="[`color-${entry.section.color}`, { 'schedule-done': entry.task.done }]" :data-schedule-task="entry.task.id">
            <td><label class="schedule-check"><input class="task-checkbox" type="checkbox" :checked="entry.task.done" :disabled="busy" :aria-label="`完成：${entry.task.title}`" @change="$emit('toggle', entry.task.id)" /></label></td>
            <td><button class="table-task-title" :disabled="busy" @click="$emit('edit', entry)">{{ entry.task.title }}</button><small class="table-task-notes" v-if="entry.task.notes">{{ entry.task.notes }}</small><small class="table-task-kind">{{ entry.task.kind === 'event' ? '事项' : '任务' }}</small></td>
            <td><span class="table-category"><i></i>{{ entry.section.title }}</span></td>
            <td>{{ entry.date || '本期内待安排' }}</td><td class="table-time">{{ taskTimeLabel(entry.task) }}</td>
            <td><span v-if="entry.task.daily"><PlannerIcon name="repeat" /> 每日</span><span v-else class="schedule-muted">不重复</span></td>
            <td><button class="icon-button" :aria-label="`编辑：${entry.task.title}`" title="编辑事项" :disabled="busy" @click="$emit('edit', entry)"><PlannerIcon name="edit" /></button></td>
          </tr>
          <tr v-if="!entries.length"><td colspan="7" class="schedule-table-empty">暂无符合条件的事项</td></tr>
        </tbody>
      </table>
    </div>

    <template v-else>
      <details v-if="undated.length" class="schedule-undated" open>
        <summary>未安排日期 <span>{{ undated.length }}</span></summary>
        <div class="schedule-undated-tasks"><PlannerScheduleTask v-for="entry in undated" :key="entry.task.id" :entry="entry" :busy="busy" @edit="$emit('edit', $event)" @toggle="$emit('toggle', $event)" /></div>
      </details>

      <div v-if="period === 'day' || period === 'week'" ref="timeline" class="schedule-timeline-scroll" role="region" :aria-label="`${periodLabel}时间表`" tabindex="0">
        <div class="schedule-timeline" :style="{ minWidth: `${timelineWidth}px`, '--schedule-tracks': timelineTracks }">
          <div class="timeline-day-head">
            <span class="timeline-corner"><PlannerIcon name="clock" /></span>
            <div v-for="day in timelineDays" :key="day" :class="{ 'is-today': day === today }"><span>{{ weekday(day) }}</span><strong>{{ shortDate(day) }}</strong><small>{{ dated(day).length }} 项</small></div>
          </div>
          <div class="timeline-allday">
            <span class="timeline-axis-label">全天</span>
            <div v-for="day in timelineDays" :key="day" class="timeline-allday-cell">
              <PlannerScheduleTask v-for="entry in dated(day).filter(item => !item.task.time)" :key="entry.task.id" :entry="entry" :busy="busy" @edit="$emit('edit', $event)" @toggle="$emit('toggle', $event)" />
              <button class="timeline-allday-add" :aria-label="`${day}添加全天事项`" :disabled="busy" @click="create(day)"><PlannerIcon name="plus" /></button>
            </div>
          </div>
          <div class="timeline-grid">
            <div class="timeline-axis"><span v-for="hour in 25" :key="hour" :style="{ top: `${(hour - 1) * hourHeight}px` }">{{ String(hour - 1).padStart(2, '0') }}:00</span></div>
            <div v-for="column in columns" :key="column.day" class="timeline-column" :data-schedule-day="column.day">
              <button v-for="hour in 24" :key="hour" class="timeline-hour" :style="{ top: `${(hour - 1) * hourHeight}px` }" :disabled="busy"
                :aria-label="`${column.day} ${String(hour - 1).padStart(2, '0')}:00 新建事项`" @click="create(column.day, `${String(hour - 1).padStart(2, '0')}:00`)"></button>
              <button v-for="entry in column.placements" :key="entry.task.id" class="timeline-event" :class="[`color-${entry.section.color}`, { 'schedule-done': entry.task.done, 'short-event': entry.end - entry.start < 60 }]"
                :style="eventStyle(entry)" :data-schedule-task="entry.task.id" :disabled="busy"
                :aria-label="`${entry.task.title}，${taskTimeLabel(entry.task)}，${entry.section.title}${entry.task.done ? '，已完成' : ''}`"
                :title="`${entry.task.title}\n${taskTimeLabel(entry.task)} · ${entry.section.title}${entry.task.notes ? '\n' + entry.task.notes : ''}`" @click="$emit('edit', entry)">
                <span class="timeline-event-time"><PlannerIcon v-if="entry.task.done" name="check" />{{ taskTimeLabel(entry.task) }}<PlannerIcon v-if="entry.task.daily" name="repeat" /></span>
                <strong>{{ entry.task.title }}</strong><small v-if="entry.end - entry.start >= 60">{{ entry.section.title }}</small>
              </button>
              <div v-if="column.day === today" class="timeline-now" :style="{ top: `${nowMinutes * minuteHeight}px` }" :aria-label="`当前时间 ${nowLabel}`"><span>{{ nowLabel }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <template v-else-if="period === 'month'">
        <div class="schedule-month" role="region" aria-label="月历">
          <div class="month-weeknames"><span v-for="name in weekNames" :key="name">{{ name }}</span></div>
          <div class="month-cells">
            <div v-for="day in cells" :key="day" class="month-cell" :class="{ outside: day.slice(0, 7) !== plan.day.slice(0, 7), chosen: focusDay === day, 'is-today': day === today }">
              <button class="month-cell-date" :disabled="day.slice(0, 7) !== plan.day.slice(0, 7)" :aria-pressed="focusDay === day" :aria-label="`${day}，${dated(day).length}项`" @click="selectDate(day)"><span>{{ Number(day.slice(8)) }}</span><small v-if="dated(day).length">{{ dated(day).length }}项</small></button>
              <button v-for="entry in dated(day).slice(0, 2)" :key="entry.task.id" class="month-event" :class="[`color-${entry.section.color}`, { 'schedule-done': entry.task.done }]" :disabled="busy" :title="entry.task.title" @click="$emit('edit', entry)"><time v-if="entry.task.time">{{ entry.task.time }}</time><span>{{ entry.task.title }}</span></button>
              <button v-if="dated(day).length > 2" class="month-more" :aria-label="`查看${day}全部${dated(day).length}项`" @click="selectDate(day)">+{{ dated(day).length - 2 }} 项</button>
              <div class="month-mobile-dots" aria-hidden="true"><i v-for="entry in dated(day).slice(0, 3)" :key="entry.task.id" :class="`color-${entry.section.color}`"></i></div>
            </div>
          </div>
        </div>
        <section ref="agenda" class="schedule-agenda" aria-label="所选日期任务">
          <header><div><h2>{{ shortDate(focusDay) }} <span>{{ weekday(focusDay) }}</span></h2><small>{{ focusedEntries.length }} 项事项</small></div><button class="icon-button" :disabled="busy" :aria-label="`${focusDay}新建事项`" title="新建事项" @click="create(focusDay)"><PlannerIcon name="plus" /></button></header>
          <PlannerScheduleTask v-for="entry in focusedEntries" :key="entry.task.id" :entry="entry" :busy="busy" @edit="$emit('edit', $event)" @toggle="$emit('toggle', $event)" />
          <p v-if="!focusedEntries.length" class="schedule-empty">这一天暂无事项</p>
        </section>
      </template>

      <template v-else>
        <div class="schedule-year" aria-label="全年月份">
          <section v-for="month in months" :key="month.key" class="year-month" :class="{ chosen: focusMonth === month.key, 'current-month': today.startsWith(month.key) }">
            <button class="year-month-heading" :aria-pressed="focusMonth === month.key" :aria-label="`查看${month.number}月任务`" @click="selectMonth(month.key)"><strong>{{ month.number }}<small>月</small></strong><span>{{ month.entries.length }} 项<PlannerIcon name="right" /></span></button>
            <progress :value="month.entries.filter(entry => entry.task.done).length" :max="month.entries.length || 1" :aria-label="`${month.number}月完成进度`"></progress>
            <button v-for="entry in month.entries.slice(0, 3)" :key="entry.task.id" class="year-event" :class="[`color-${entry.section.color}`, { 'schedule-done': entry.task.done }]" :disabled="busy" :title="entry.task.title" @click="$emit('edit', entry)"><time>{{ Number(entry.date.slice(8)) }}日</time><span>{{ entry.task.title }}</span></button>
            <span v-if="!month.entries.length" class="year-empty">暂无安排</span>
            <button v-if="month.entries.length > 3" class="month-more" @click="selectMonth(month.key)">查看全部 {{ month.entries.length }} 项</button>
          </section>
        </div>
        <section ref="agenda" class="schedule-agenda" aria-label="所选月份任务">
          <header><div><h2>{{ Number(focusMonth.slice(5)) }}月安排</h2><small>{{ focusedEntries.length }} 项事项</small></div><button class="icon-button" :disabled="busy" :aria-label="`${focusMonth}新建事项`" title="新建事项" @click="create(`${focusMonth}-01`)"><PlannerIcon name="plus" /></button></header>
          <PlannerScheduleTask v-for="entry in focusedEntries" :key="entry.task.id" :entry="entry" :show-date="true" :busy="busy" @edit="$emit('edit', $event)" @toggle="$emit('toggle', $event)" />
          <p v-if="!focusedEntries.length" class="schedule-empty">本月暂无事项</p>
        </section>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PlannerIcon from './PlannerIcon.vue'
import PlannerScheduleTask from './PlannerScheduleTask.vue'
import { dayKey, monthCells, scheduleEntries, scheduleLayout, taskTimeLabel, weekDays,
  type DailyPlan, type ScheduleEntry, type SchedulePlacement } from './planner'

const props = defineProps<{ plan: DailyPlan; busy: boolean; todoOnly: boolean; selectedDay: string }>()
const emit = defineEmits<{ edit: [entry: ScheduleEntry]; toggle: [id: string]; create: [value: { date: string; time: string; sectionId: string }] }>()
const mode = ref<'calendar' | 'table'>('calendar')
const category = ref('')
const period = computed(() => props.plan.period || 'day')
const periodLabel = computed(() => ({ day: '日', week: '周', month: '月', year: '年' })[period.value])
const entries = computed(() => scheduleEntries(props.plan, category.value, props.todoOnly))
const entriesByDay = computed(() => {
  const groups = new Map<string, ScheduleEntry[]>()
  for (const entry of entries.value) {
    if (!groups.has(entry.date)) groups.set(entry.date, [])
    groups.get(entry.date)!.push(entry)
  }
  return groups
})
const dated = (day: string) => entriesByDay.value.get(day) || []
const undated = computed(() => dated(''))
const focusDay = ref(props.selectedDay)
const focusMonth = ref(props.selectedDay.slice(0, 7))
const now = ref(new Date())
const today = computed(() => dayKey(now.value))
const nowMinutes = computed(() => now.value.getHours() * 60 + now.value.getMinutes())
const nowLabel = computed(() => `${String(now.value.getHours()).padStart(2, '0')}:${String(now.value.getMinutes()).padStart(2, '0')}`)
const weekNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const weekday = (day: string) => weekNames[(new Date(`${day}T12:00:00`).getDay() + 6) % 7]
const shortDate = (day: string) => `${Number(day.slice(5, 7))}月${Number(day.slice(8))}日`
const cells = computed(() => monthCells(props.plan.day))
const months = computed(() => Array.from({ length: 12 }, (_, i) => {
  const key = `${props.plan.day.slice(0, 4)}-${String(i + 1).padStart(2, '0')}`
  return { key, number: i + 1, entries: entries.value.filter(entry => entry.date.startsWith(key)) }
}))
const focusedEntries = computed(() => period.value === 'year'
  ? entries.value.filter(entry => entry.date.startsWith(focusMonth.value)) : dated(focusDay.value))
const timelineDays = computed(() => period.value === 'week' ? weekDays(props.plan.day) : [props.plan.day])
const minuteHeight = 1.6
const hourHeight = minuteHeight * 60
const columns = computed(() => timelineDays.value.map(day => ({ day, placements: scheduleLayout(dated(day)) })))
const columnWidths = computed(() => columns.value.map(column => Math.max(period.value === 'week' ? 160 : 220,
  ...column.placements.map(entry => entry.lanes * 132))))
const timelineWidth = computed(() => 58 + columnWidths.value.reduce((sum, width) => sum + width, 0))
const timelineTracks = computed(() => `58px ${columnWidths.value.map(width => `minmax(${width}px, 1fr)`).join(' ')}`)
const timeline = ref<HTMLElement | null>(null)
const agenda = ref<HTMLElement | null>(null)
async function revealAgenda() {
  await nextTick()
  const heading = agenda.value?.querySelector('header')
  if (heading && heading.getBoundingClientRect().bottom > window.innerHeight - 100) heading.scrollIntoView({ block: 'center' })
}
function selectDate(day: string) { focusDay.value = day; void revealAgenda() }
function selectMonth(month: string) { focusMonth.value = month; void revealAgenda() }
function eventStyle(entry: SchedulePlacement) {
  return {
    top: `${entry.start * minuteHeight}px`, height: `${(entry.end - entry.start) * minuteHeight - 3}px`,
    left: `calc(${entry.lane / entry.lanes * 100}% + 3px)`, width: `calc(${100 / entry.lanes}% - 6px)`
  }
}
function create(date: string, time = '') { emit('create', { date, time, sectionId: category.value }) }
async function scrollToSchedule() {
  await nextTick()
  if (!timeline.value) return
  const starts = columns.value.flatMap(column => column.placements.map(entry => entry.start))
  // Start near the first daytime task, while keeping midnight events reachable above.
  const minute = starts.find(value => value >= 360) ?? starts[0] ?? 480
  timeline.value.scrollTop = Math.max(0, minute - 15) * minuteHeight
  const todayIndex = timelineDays.value.indexOf(today.value)
  if (todayIndex > 0) {
    const column = timeline.value.querySelectorAll<HTMLElement>('.timeline-column')[todayIndex]
    timeline.value.scrollLeft = Math.max(0, column.offsetLeft - 58)
  }
}
watch(() => `${period.value}:${props.plan.day}`, () => {
  category.value = ''
  focusDay.value = props.selectedDay
  focusMonth.value = props.selectedDay.slice(0, 7)
  void scrollToSchedule()
})
watch(() => props.plan.sections, sections => {
  if (category.value && !sections.some(section => section.id === category.value)) category.value = ''
})
watch(mode, () => { if (mode.value === 'calendar') void scrollToSchedule() })
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => { void scrollToSchedule(); timer = setInterval(() => { now.value = new Date() }, 60_000) })
onBeforeUnmount(() => { clearInterval(timer) })
</script>

<style src="./schedule.css"></style>
