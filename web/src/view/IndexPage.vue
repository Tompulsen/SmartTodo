<template>
  <div class="planner-shell" :class="{ 'drag-active': drag?.active, 'schedule-screen': scheduleView }">
    <aside class="desktop-rail" aria-label="主导航">
      <a href="/index" class="rail-brand" aria-label="SmartTodo 首页"><PlannerIcon name="tasks" /></a>
      <button class="rail-item" :class="{ selected: !scheduleView }" :aria-current="!scheduleView ? 'page' : undefined" @click="setScheduleView(false)"><PlannerIcon name="calendar" /><span>计划</span></button>
      <button class="rail-item" :class="{ selected: scheduleView }" :aria-current="scheduleView ? 'page' : undefined" @click="setScheduleView(true)"><PlannerIcon name="grid" /><span>视图</span></button>
      <router-link class="rail-item" to="/tomato"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <button class="rail-item" @click="openDialog('stats')"><PlannerIcon name="chart" /><span>统计</span></button>
      <router-link class="rail-item rail-tools" to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </aside>

    <main class="planner-main">
      <header class="planner-header">
        <div class="brand-line"><span class="brand-word">SmartTodo<span class="brand-dot"></span></span><span class="brand-subtitle">把时间留给重要的事</span></div>
        <div class="header-actions">
          <span class="save-status" role="status"><PlannerIcon :name="saving || loading ? 'clock' : 'saved'" />{{ saving ? '保存中' : loading ? '读取中' : error ? '保存状态异常' : '已保存至本地' }}</span>
          <button class="icon-button reminder-button" :class="{ enabled: reminderPermission === 'granted' }"
            :aria-label="reminderControlLabel" :data-tip="reminderControlLabel" @click="enableReminders">
            <PlannerIcon :name="reminderIcon" />
          </button>
          <router-link class="icon-button" to="/tools" aria-label="工具箱" data-tip="工具箱"><PlannerIcon name="more" /></router-link>
        </div>
      </header>

      <div class="period-toolbar">
        <div class="period-switch" role="group" aria-label="计划周期">
          <button v-for="item in periods" :key="item.value" :class="{ selected: selectedPeriod === item.value }"
            :aria-pressed="selectedPeriod === item.value" :disabled="busy || !!drag" @click="selectDay(selectedDay, item.value)">
            {{ item.label }}<span>计划</span>
          </button>
        </div>
        <div class="period-progress">
          <span>完成进度 <strong>{{ completion }}%</strong></span>
          <progress :value="counts.done" :max="counts.total || 1" aria-label="计划完成进度"></progress>
        </div>
      </div>

      <section class="calendar-band" aria-label="日期选择">
        <div class="calendar-topline">
          <div class="planner-tabs" role="tablist" aria-label="事项范围">
            <button role="tab" :aria-selected="tab === 'all'" :class="{ active: tab === 'all' }" @click="tab = 'all'">日程</button>
            <button role="tab" :aria-selected="tab === 'todo'" :class="{ active: tab === 'todo' }" @click="tab = 'todo'">待办<span class="tab-count">{{ counts.total - counts.done }}</span></button>
          </div>
          <div class="month-controls">
            <label class="month-picker" :class="{ 'year-picker': selectedPeriod === 'year' }">
              <span>{{ pickerCaption }}</span><PlannerIcon name="calendar" />
              <input v-if="selectedPeriod === 'year'" type="number" min="1900" max="9998" aria-label="选择年份"
                :value="Number(selectedDay.slice(0, 4))" :disabled="busy" @change="dateChanged" />
              <input v-else :type="selectedPeriod === 'month' ? 'month' : 'date'"
                :aria-label="selectedPeriod === 'month' ? '选择月份' : '选择日期'"
                :value="selectedPeriod === 'month' ? selectedDay.slice(0, 7) : selectedDay" :disabled="busy" @change="dateChanged" />
            </label>
            <div class="week-controls">
              <button class="icon-button" :aria-label="`上一${navigationUnit}`" :data-tip="`上一${navigationUnit}`" :disabled="busy || !!drag" @click="navigatePeriod(-1)"><PlannerIcon name="left" /></button>
              <button class="today-button" :disabled="busy || !!drag" @click="selectDay(todayKey())">{{ currentPeriodLabel }}</button>
              <button class="icon-button" :aria-label="`下一${navigationUnit}`" :data-tip="`下一${navigationUnit}`" :disabled="busy || !!drag" @click="navigatePeriod(1)"><PlannerIcon name="right" /></button>
            </div>
          </div>
        </div>
        <div v-if="selectedPeriod === 'day'" class="week-strip">
          <button v-for="(day, index) in week" :key="day" class="day-button"
            :class="{ selected: day === selectedDay, today: day === today, weekend: index > 4 }"
            :aria-label="`${day} ${weekNames[index]}`" :aria-pressed="day === selectedDay" :disabled="busy" @click="selectDay(day)">
            <span class="weekday">{{ weekNames[index] }}</span>
            <span class="day-disc"><span class="day-number">{{ Number(day.slice(8)) }}</span><span class="day-lunar">{{ day === today ? '今天' : lunarDay(day) }}</span></span>
            <span class="day-marker" :class="{ populated: overview[day]?.total, complete: overview[day]?.total && overview[day]?.total === overview[day]?.done }"></span>
          </button>
        </div>
        <div v-else-if="!scheduleView" class="period-context">
          <div class="period-range"><PlannerIcon name="calendar" /><div><strong>{{ dateCaption }}</strong><span>{{ periodDays }} 天<span class="heading-dot">·</span>{{ counts.total - counts.done }} 项待办</span></div></div>
          <div v-if="selectedPeriod === 'month' || selectedPeriod === 'year'" class="period-shortcuts" :aria-label="selectedPeriod === 'month' ? '月份切换' : '年份切换'">
            <button v-for="shortcut in periodShortcuts" :key="shortcut.day" :aria-pressed="shortcut.active"
              :class="{ selected: shortcut.active }" :disabled="busy" @click="selectDay(shortcut.day)">{{ shortcut.label }}</button>
          </div>
          <div v-else class="week-range-days" aria-label="本周日期">
            <span v-for="(day, index) in week" :key="day" :class="{ today: day === today }"><small>{{ weekNames[index] }}</small><strong>{{ Number(day.slice(8)) }}</strong></span>
          </div>
        </div>
      </section>

      <div class="board-heading">
        <div class="board-title">
          <div class="title-line"><h1>{{ plan?.title || defaultTitle }}</h1><button class="icon-button subtle" :aria-label="`编辑${scopeLabel}主题`" :data-tip="`编辑${scopeLabel}主题`" :disabled="busy || !plan" @click="openTitle"><PlannerIcon name="edit" /></button></div>
          <p>{{ dateCaption }}<span class="heading-dot">·</span><span>{{ counts.done }} / {{ counts.total }} 已完成</span></p>
        </div>
        <div class="board-actions">
          <div v-if="!scheduleView" class="view-switch" role="group" aria-label="布局">
            <button :class="{ selected: layout === 'grid' }" :aria-pressed="layout === 'grid'" aria-label="宫格视图" title="宫格视图" @click="layout = 'grid'"><PlannerIcon name="grid" /></button>
            <button :class="{ selected: layout === 'list' }" :aria-pressed="layout === 'list'" aria-label="列表视图" title="列表视图" @click="layout = 'list'"><PlannerIcon name="list" /></button>
          </div>
          <button v-if="!scheduleView" class="outline-button add-section" :disabled="busy || !plan || plan.sections.length >= 24" @click="openSection()"><PlannerIcon name="plus" /><span>添加宫格</span></button>
          <button class="primary-button header-add" :disabled="busy || !plan" @click="openTask()"><PlannerIcon name="plus" />新建事项</button>
        </div>
      </div>

      <div v-if="error" class="planner-error" role="alert"><span>{{ error }}</span><button class="text-button" :disabled="busy" @click="loadDay(selectedDay)"><PlannerIcon name="refresh" />重新加载</button></div>
      <div v-if="loading" class="planner-loading" role="status"><span class="loading-line"></span>正在读取计划</div>

      <PlannerSchedule v-else-if="plan && scheduleView" :plan="plan" :selected-day="selectedDay" :busy="saving" :todo-only="tab === 'todo'"
        @edit="openTask($event.section, $event.task)" @toggle="toggleTask" @create="createScheduledTask" />
      <div v-else-if="plan" class="day-board" :class="{ 'list-layout': layout === 'list', 'many-sections': plan.sections.length > 4 }" :aria-busy="saving">
        <article v-for="(section, sectionIndex) in plan.sections" :key="section.id" class="quadrant"
          :class="[`color-${section.color}`, { 'drag-target': dropTarget?.sectionId === section.id }]" :data-drop-section="section.id"
          :aria-label="section.title">
          <header class="quadrant-header">
            <div class="section-title-wrap">
              <button class="section-title-button" :disabled="saving" :aria-label="`编辑宫格：${section.title}`" @click="openSection(section)">
                <h2><span>{{ section.title }}</span></h2>
              </button>
              <span v-if="section.start || section.end" class="section-time"><PlannerIcon name="clock" />{{ section.start || '00:00' }} - {{ section.end || '24:00' }}</span>
            </div>
            <div class="section-actions">
              <span class="section-count">{{ section.tasks.filter(task => !task.done).length }}</span>
              <button class="icon-button subtle section-edit" :disabled="saving" :aria-label="`设置宫格：${section.title}`" data-tip="宫格设置" @click="openSection(section)"><PlannerIcon name="more" /></button>
            </div>
          </header>

          <ul class="section-tasks" :class="{ 'drop-at-end': dropTarget?.sectionId === section.id && dropTarget.beforeId === null }"
            :aria-label="`${section.title}的事项`">
            <PlannerTaskRow v-for="task in visibleTasks(section)" :key="task.id" :task="task" :period="selectedPeriod"
              :rank="section.tasks.findIndex(item => item.id === task.id) + 1" :busy="saving"
              :dragging="!!drag?.active && drag.taskId === task.id" :drop-before="dropTarget?.beforeId === task.id"
              @toggle="toggleTask" @edit="openTask(section, $event)" @drag="startDrag" @move="reorderTask" />
          </ul>

          <div v-if="!visibleTasks(section).length" class="section-empty"
            :class="{ 'empty-drop-target': dropTarget?.sectionId === section.id }">
            <PlannerIcon v-if="dropTarget?.sectionId === section.id" name="down" class="empty-drop-icon" />
            <img v-if="sectionIndex % 4 === 2" class="planner-sticker" src="/planner/focus.png" alt="" draggable="false" />
            <img v-else-if="sectionIndex % 4 === 3" class="planner-sticker" src="/planner/rest.png" alt="" draggable="false" />
            <div v-else class="empty-mark" aria-hidden="true"><PlannerIcon :name="sectionIndex % 4 === 0 ? 'focus' : 'note'" /></div>
            <span>{{ section.tasks.length && tab === 'todo' ? '已全部完成' : '留一点空间，给重要的事' }}</span>
          </div>
          <div class="section-bottom">
            <button class="section-add" :disabled="saving" :aria-label="`在${section.title}中添加事项`" @click="openTask(section)"><PlannerIcon name="plus" /><span>添加事项</span></button>
            <span v-if="section.tasks.some(task => task.done)" class="section-done-count"><PlannerIcon name="check" />{{ section.tasks.filter(task => task.done).length }} 完成</span>
          </div>
        </article>
      </div>

      <footer v-if="plan && !loading" class="board-footer">
        <span><span class="footer-dot"></span>{{ selectedPeriod === 'day' ? selectedDay : dateCaption }}<span class="heading-dot">·</span>{{ plan.sections.length }} 个宫格</span>
        <span>{{ scopeLabel }}计划</span>
      </footer>
    </main>

    <button class="mobile-fab" aria-label="新建事项" :disabled="busy || !plan" @click="openTask()"><PlannerIcon name="plus" /></button>
    <nav class="mobile-nav" aria-label="主导航">
      <button :class="{ selected: !scheduleView }" :aria-current="!scheduleView ? 'page' : undefined" @click="setScheduleView(false)"><PlannerIcon name="calendar" /><span>计划</span></button>
      <button :class="{ selected: scheduleView }" :aria-current="scheduleView ? 'page' : undefined" @click="setScheduleView(true)"><PlannerIcon name="grid" /><span>视图</span></button>
      <router-link to="/tomato"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <button @click="openDialog('stats')"><PlannerIcon name="chart" /><span>统计</span></button>
      <router-link to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </nav>

    <PlannerDialog :open="dialog === 'task'" :title="taskForm.id ? '编辑事项' : '新建事项'" :busy="saving" @close="closeDialog">
      <form class="planner-form" @submit.prevent="saveTask">
        <div class="form-date"><PlannerIcon name="calendar" />{{ dateCaption }}</div>
        <div class="kind-switch" role="group" aria-label="事项类型">
          <button type="button" :class="{ selected: taskForm.kind === 'task' }" :aria-pressed="taskForm.kind === 'task'" :disabled="saving" @click="taskForm.kind = 'task'"><PlannerIcon name="tasks" />任务</button>
          <button type="button" :class="{ selected: taskForm.kind === 'event' }" :aria-pressed="taskForm.kind === 'event'" :disabled="saving" @click="taskForm.kind = 'event'"><PlannerIcon name="note" />事项</button>
        </div>
        <label>标题<input v-model="taskForm.title" autofocus required maxlength="200" placeholder="想完成什么？" :disabled="saving" /></label>
        <label>所属宫格<select v-model="taskForm.sectionId" :disabled="saving"><option v-for="section in plan?.sections" :key="section.id" :value="section.id">{{ section.title }}</option></select></label>
        <label v-if="selectedPeriod !== 'day'">执行日期（可选）<input ref="taskDateInput" v-model="taskForm.scheduledDate" type="date"
          :min="bounds.start" :max="bounds.end" :disabled="saving" :aria-invalid="!!taskDateError"
          :aria-describedby="taskDateError ? 'task-date-error' : undefined" /></label>
        <p v-if="taskDateError" id="task-date-error" class="form-error" role="alert">{{ taskDateError }}</p>
        <div class="task-time-fields">
          <div class="form-columns">
            <label>开始时间<input ref="taskStartInput" v-model="taskForm.time" type="time" :disabled="saving"
              :aria-invalid="!!taskTimeError && !taskForm.time" :aria-describedby="taskTimeError ? 'task-time-error' : undefined" /></label>
            <label>结束时间（可选）<input ref="taskEndInput" v-model="taskForm.endTime" type="time" :disabled="saving"
              :aria-invalid="!!taskTimeError" :aria-describedby="taskTimeError ? 'task-time-error' : undefined" /></label>
          </div>
          <p v-if="taskTimeError" id="task-time-error" class="form-error" role="alert">{{ taskTimeError }}</p>
        </div>
        <label>备注<textarea v-model="taskForm.notes" maxlength="5000" rows="3" placeholder="补充细节…" :disabled="saving"></textarea></label>
        <label v-if="selectedPeriod === 'day'" class="check-label daily-setting">
          <span><PlannerIcon name="repeat" />每日必做</span>
          <input v-model="taskForm.daily" type="checkbox" role="switch" :disabled="saving" />
        </label>
        <label v-if="taskForm.id" class="check-label"><input v-model="taskForm.done" type="checkbox" :disabled="saving" />已完成</label>
        <div v-if="taskForm.id" class="task-order-controls">
          <span>优先顺序</span>
          <button type="button" class="outline-button" :disabled="saving || taskPosition <= 0" @click="moveEditingTask(-1)"><PlannerIcon name="up" />上移</button>
          <button type="button" class="outline-button" :disabled="saving || taskPosition < 0 || taskPosition >= editingSectionSize - 1" @click="moveEditingTask(1)"><PlannerIcon name="down" />下移</button>
        </div>
        <div v-if="confirmDelete" class="delete-confirm"><p>{{ editingDailyTask ? '确定删除这条事项，并停止此日期及之后的每日重复？' : '确定删除这条事项？' }}</p><button type="button" class="text-button" @click="confirmDelete = false">取消</button><button type="button" class="danger-button" :disabled="saving" @click="deleteTask">确认删除</button></div>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <footer class="dialog-footer">
          <button v-if="taskForm.id && !confirmDelete" class="icon-button danger-text" type="button" aria-label="删除事项" title="删除事项" :disabled="saving" @click="confirmDelete = true"><PlannerIcon name="delete" /></button>
          <div class="dialog-footer-spacer"></div>
          <button class="outline-button" type="button" :disabled="saving" @click="closeDialog">取消</button>
          <button class="primary-button" type="submit" :disabled="saving"><PlannerIcon name="check" />{{ saving ? '保存中' : '保存事项' }}</button>
        </footer>
      </form>
    </PlannerDialog>

    <PlannerDialog :open="dialog === 'section'" :title="sectionForm.id ? '编辑宫格' : '添加宫格'" :busy="saving" @close="closeDialog">
      <form class="planner-form" @submit.prevent="saveSection">
        <div class="form-date"><PlannerIcon name="calendar" />{{ dateCaption }}</div>
        <label>宫格主题<input v-model="sectionForm.title" autofocus required maxlength="40" placeholder="例如：上午、工作计划、个人时间" :disabled="saving" /></label>
        <fieldset class="color-field"><legend>主题颜色</legend><div class="color-options">
          <button v-for="color in colors" :key="color.value" type="button" class="color-swatch" :class="[`color-${color.value}`, { chosen: sectionForm.color === color.value }]"
            :aria-label="color.label" :aria-pressed="sectionForm.color === color.value" :title="color.label" :disabled="saving" @click="sectionForm.color = color.value"><PlannerIcon v-if="sectionForm.color === color.value" name="check" /></button>
        </div></fieldset>
        <div v-if="selectedPeriod === 'day'" class="form-columns">
          <label>开始时间<input v-model="sectionForm.start" type="time" :disabled="saving" /></label>
          <label>结束时间<input v-model="sectionForm.end" type="time" :disabled="saving" /></label>
        </div>
        <div v-if="sectionForm.id" class="task-order-controls">
          <span>宫格位置</span><button type="button" class="outline-button" :disabled="saving || sectionPosition <= 0" @click="moveSection(-1)"><PlannerIcon name="up" />前移</button>
          <button type="button" class="outline-button" :disabled="saving || sectionPosition >= (plan?.sections.length || 0) - 1" @click="moveSection(1)"><PlannerIcon name="down" />后移</button>
        </div>
        <div v-if="confirmDelete" class="delete-confirm">
          <p>确定删除「{{ sectionForm.title }}」宫格？</p>
          <label v-if="sectionTaskCount">现有 {{ sectionTaskCount }} 条事项移至<select v-model="deleteMoveTarget"><option v-for="section in plan?.sections.filter(item => item.id !== sectionForm.id)" :key="section.id" :value="section.id">{{ section.title }}</option></select></label>
          <button type="button" class="text-button" @click="confirmDelete = false">取消</button><button type="button" class="danger-button" :disabled="saving" @click="deleteSection">确认删除</button>
        </div>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <footer class="dialog-footer">
          <button v-if="sectionForm.id && !confirmDelete" class="icon-button danger-text" type="button" aria-label="删除宫格" title="删除宫格" :disabled="saving || plan?.sections.length === 1" @click="confirmDelete = true"><PlannerIcon name="delete" /></button>
          <div class="dialog-footer-spacer"></div><button class="outline-button" type="button" :disabled="saving" @click="closeDialog">取消</button>
          <button class="primary-button" type="submit" :disabled="saving"><PlannerIcon name="check" />{{ saving ? '保存中' : '保存宫格' }}</button>
        </footer>
      </form>
    </PlannerDialog>

    <PlannerDialog :open="dialog === 'title'" :title="`${scopeLabel}主题`" :busy="saving" @close="closeDialog">
      <form class="planner-form" @submit.prevent="saveTitle">
        <div class="form-date"><PlannerIcon name="calendar" />{{ dateCaption }}</div>
        <label>主题名称<input v-model="dayTitle" autofocus required maxlength="60" :disabled="saving" /></label>
        <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
        <footer class="dialog-footer"><div class="dialog-footer-spacer"></div><button class="outline-button" type="button" :disabled="saving" @click="closeDialog">取消</button><button class="primary-button" type="submit" :disabled="saving">保存主题</button></footer>
      </form>
    </PlannerDialog>

    <PlannerDialog :open="dialog === 'stats'" :title="`${scopeLabel}统计`" @close="closeDialog">
      <div class="planner-form">
        <div class="form-date"><PlannerIcon name="calendar" />{{ dateCaption }}</div>
        <div class="daily-stats"><div><strong>{{ counts.total }}</strong><span>全部事项</span></div><div><strong>{{ counts.done }}</strong><span>已完成</span></div><div><strong>{{ counts.total ? Math.round(counts.done / counts.total * 100) : 0 }}<small>%</small></strong><span>完成率</span></div></div>
        <div v-for="section in plan?.sections" :key="section.id" class="section-stat" :class="`color-${section.color}`">
          <div><span>{{ section.title }}</span><span>{{ section.tasks.filter(task => task.done).length }} / {{ section.tasks.length }}</span></div>
          <progress :value="section.tasks.filter(task => task.done).length" :max="section.tasks.length || 1"></progress>
        </div>
      </div>
    </PlannerDialog>

    <PlannerDialog :open="reminderOpen" title="到点提醒" @close="dismissReminders">
      <div class="planner-form reminder-dialog">
        <div class="reminder-lead">
          <span class="reminder-lead-icon"><PlannerIcon name="bell" /></span>
          <div><strong>{{ reminders.length === 1 ? '现在该处理这项任务了' : `现在有 ${reminders.length} 项任务到时间了` }}</strong><span>{{ dateCaptionFor(todayKey()) }}</span></div>
        </div>
        <ul class="reminder-list" aria-label="到点任务">
          <li v-for="reminder in reminders" :key="reminderKey(todayKey(), reminder.task, reminder.period)">
            <button type="button" class="reminder-task" @click="openReminderTask(reminder)">
              <span><strong>{{ reminder.task.title }}</strong><small>{{ periodName(reminder.period || 'day') }}计划<i>·</i>{{ reminder.sectionTitle }}<i>·</i><span class="task-time">{{ taskTimeLabel(reminder.task) }}</span></small></span>
              <PlannerIcon name="right" />
            </button>
            <button type="button" class="icon-button reminder-complete" :aria-label="`完成：${reminder.task.title}`"
              title="标记完成" :disabled="saving" @click="completeReminder(reminder)"><PlannerIcon name="check" /></button>
          </li>
        </ul>
        <p v-if="reminderPermission !== 'granted'" class="reminder-permission-note">
          <PlannerIcon name="bell" />开启浏览器通知后，切到后台也能收到提醒
        </p>
        <footer class="dialog-footer">
          <div class="dialog-footer-spacer"></div>
          <button class="outline-button" type="button" @click="dismissReminders">稍后处理</button>
          <button class="primary-button" type="button" @click="openReminderTask(reminders[0])"><PlannerIcon name="right" />查看事项</button>
        </footer>
      </div>
    </PlannerDialog>

    <div v-if="toast" class="planner-toast" role="status"><PlannerIcon name="check" />{{ toast }}</div>
    <Teleport to="body">
      <div v-if="drag?.active" class="task-drag-preview" :class="{ 'no-drop-target': !dropTarget }" :style="dragPreviewStyle">
        <PlannerIcon name="grip" /><div><span>{{ drag.title }}</span><small v-if="dropSectionTitle"><PlannerIcon name="right" />{{ dropSectionTitle }}</small></div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import PlannerDialog from '@/components/planner/PlannerDialog.vue'
import PlannerTaskRow from '@/components/planner/PlannerTaskRow.vue'
import PlannerSchedule from '@/components/planner/PlannerSchedule.vue'
import {
  clonePlan, dayKey, dropBeforeTask, dragScrollSpeed, moveTask, moveTaskBy, planCounts, planRequest, PlanRequestError,
  dueReminderTasks, reminderKey, taskTimeLabel, shiftDay, validDay, weekDays,
  periodBounds, shiftPeriod, planPath, samePlan, validPeriod,
  type DailyPlan, type DayCounts, type PlanColor, type PlanSection, type PlanTask, type PlannerReminder, type PlanPeriod
} from '@/components/planner/planner'

const route = useRoute()
const router = useRouter()
const today = dayKey(new Date())
const selectedDay = ref(validDay(route.query.date) ? route.query.date : today)
const selectedPeriod = ref<PlanPeriod>(validPeriod(route.query.period) ? route.query.period : 'day')
const periods: { value: PlanPeriod; label: string }[] = [
  { value: 'day', label: '日' }, { value: 'week', label: '周' }, { value: 'month', label: '月' }, { value: 'year', label: '年' }
]
const periodName = (period: PlanPeriod) => periods.find(item => item.value === period)!.label
const scopeLabel = computed(() => selectedPeriod.value === 'day' ? '当日' : `本${periodName(selectedPeriod.value)}`)
const defaultTitle = computed(() => `一${periodName(selectedPeriod.value)}计划`)
const bounds = computed(() => periodBounds(selectedPeriod.value, selectedDay.value))
const periodDays = computed(() => Math.round((new Date(`${bounds.value.end}T12:00:00`).getTime() - new Date(`${bounds.value.start}T12:00:00`).getTime()) / 86400000) + 1)
const pickerCaption = computed(() => selectedPeriod.value === 'year' ? `${selectedDay.value.slice(0, 4)} 年` : selectedDay.value.slice(0, 7).replace('-', '.'))
const navigationUnit = computed(() => selectedPeriod.value === 'day' ? '周' : periodName(selectedPeriod.value))
const currentPeriodLabel = computed(() => selectedPeriod.value === 'day' ? '今天' : `本${periodName(selectedPeriod.value)}`)
const periodShortcuts = computed(() => {
  const year = Number(selectedDay.value.slice(0, 4))
  if (selectedPeriod.value === 'month') return Array.from({ length: 12 }, (_, index) => ({
    day: `${year}-${String(index + 1).padStart(2, '0')}-01`, label: `${index + 1}月`,
    active: index + 1 === Number(selectedDay.value.slice(5, 7))
  }))
  return Array.from({ length: 5 }, (_, index) => year - 2 + index).filter(value => value >= 1900 && value <= 9998)
    .map(value => ({ day: `${value}-01-01`, label: `${value}年`, active: value === year }))
})
const plan = ref<DailyPlan | null>(null)
const loading = ref(true)
const saving = ref(false)
const busy = computed(() => loading.value || saving.value)
const error = ref('')
const modalError = ref('')
const tab = ref<'all' | 'todo'>('all')
const layout = ref<'grid' | 'list'>('grid')
const scheduleView = computed(() => route.query.view === 'schedule')
const overview = ref<Record<string, DayCounts>>({})
const reminderPlans = ref<DailyPlan[]>([])
const reminders = ref<PlannerReminder[]>([])
const reminderOpen = ref(false)
type ReminderPermission = NotificationPermission | 'unsupported'
const reminderPermission = ref<ReminderPermission>(typeof Notification === 'undefined' ? 'unsupported' : Notification.permission)
const week = computed(() => weekDays(selectedDay.value))
const weekNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const dateCaption = computed(() => {
  if (selectedPeriod.value === 'day') return dateCaptionFor(selectedDay.value)
  if (selectedPeriod.value === 'month') return `${Number(selectedDay.value.slice(0, 4))}年${Number(selectedDay.value.slice(5, 7))}月`
  if (selectedPeriod.value === 'year') return `${Number(selectedDay.value.slice(0, 4))}年`
  return `${bounds.value.start.replace(/-/g, '.')} - ${bounds.value.end.replace(/-/g, '.')}`
})
const reminderIcon = computed(() => reminderPermission.value === 'denied' ? 'bell-slash' : 'bell')
const reminderControlLabel = computed(() => {
  if (reminderPermission.value === 'granted') return '系统到点提醒已开启'
  if (reminderPermission.value === 'denied') return '浏览器通知已关闭，页面弹窗仍可用'
  if (reminderPermission.value === 'unsupported') return '使用页面弹窗提醒'
  return '开启系统到点提醒'
})
const counts = computed(() => plan.value ? planCounts(plan.value) : { total: 0, done: 0 })
const completion = computed(() => counts.value.total ? Math.round(counts.value.done / counts.value.total * 100) : 0)
const colors: { value: PlanColor; label: string }[] = [
  { value: 'rose', label: '珊瑚粉' }, { value: 'gold', label: '明黄' }, { value: 'sage', label: '草绿' },
  { value: 'blue', label: '天空蓝' }, { value: 'lilac', label: '淡紫' }, { value: 'teal', label: '青绿' }
]
type DialogType = 'task' | 'section' | 'title' | 'stats' | null
const dialog = ref<DialogType>(null)
const confirmDelete = ref(false)
const toast = ref('')
let toastTimer: ReturnType<typeof setTimeout>
let loadSequence = 0
let overviewSequence = 0
let reminderTimer: number | undefined
let reminderLastChecked = new Date(Date.now() - 15_000)
let reminderPlanRequest: Promise<DailyPlan[]> | null = null
let reminderPlansLoadedAt = 0
let reminderPlansDay = ''
let reminderCheckInProgress = false
const taskForm = ref({ id: '', title: '', notes: '', time: '', endTime: '', scheduledDate: '', kind: 'task' as 'task' | 'event', done: false, daily: false, sectionId: '' })
const taskStartInput = ref<HTMLInputElement | null>(null)
const taskEndInput = ref<HTMLInputElement | null>(null)
const taskDateInput = ref<HTMLInputElement | null>(null)
const taskDateError = computed(() => {
  if (selectedPeriod.value === 'day') return ''
  const { scheduledDate, time } = taskForm.value
  if (time && !scheduledDate) return '设置具体时间时，请同时选择执行日期。'
  if (scheduledDate && (!validDay(scheduledDate) || scheduledDate < bounds.value.start || scheduledDate > bounds.value.end)) return '执行日期须在当前计划周期内。'
  return ''
})
const taskTimeError = computed(() => {
  const { time, endTime } = taskForm.value
  if (!endTime) return ''
  if (!time) return '请先设置开始时间。'
  if (endTime <= time) return '结束时间须晚于开始时间，请选择当天较晚的时间。'
  return ''
})
const sectionForm = ref({ id: '', title: '', color: 'rose' as PlanColor, start: '', end: '' })
const dayTitle = ref('')
const deleteMoveTarget = ref('')
const editingTaskSection = computed(() => plan.value?.sections.find(section => section.tasks.some(task => task.id === taskForm.value.id)))
const editingDailyTask = computed(() => !!editingTaskSection.value?.tasks.find(task => task.id === taskForm.value.id)?.daily)
const taskPosition = computed(() => editingTaskSection.value?.tasks.findIndex(task => task.id === taskForm.value.id) ?? -1)
const editingSectionSize = computed(() => editingTaskSection.value?.tasks.length || 0)
const sectionPosition = computed(() => plan.value?.sections.findIndex(section => section.id === sectionForm.value.id) ?? -1)
const sectionTaskCount = computed(() => plan.value?.sections.find(section => section.id === sectionForm.value.id)?.tasks.length || 0)

function lunarDay(day: string) {
  try {
    const parts = new Intl.DateTimeFormat('zh-CN-u-ca-chinese', { day: 'numeric', month: 'short' }).formatToParts(new Date(`${day}T12:00:00`))
    const value = Number(parts.find(part => part.type === 'day')?.value)
    const numerals = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    if (value === 1) return parts.find(part => part.type === 'month')?.value || '初一'
    if (value <= 10) return `初${numerals[value - 1]}`
    if (value < 20) return `十${numerals[value - 11]}`
    if (value === 20) return '二十'
    if (value < 30) return `廿${numerals[value - 21]}`
    return '三十'
  } catch { return '' }
}

function todayKey() {
  return dayKey(new Date())
}
function dateCaptionFor(day: string) {
  return new Date(`${day}T12:00:00`).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })
}

async function loadDay(day: string, period: PlanPeriod = selectedPeriod.value) {
  if (saving.value || !validDay(day) || !validPeriod(period)) return
  const sequence = ++loadSequence
  selectedDay.value = day
  selectedPeriod.value = period
  loading.value = true
  error.value = ''
  try {
    const result = await planRequest<DailyPlan>(planPath(period, day))
    if (sequence !== loadSequence) return
    plan.value = result
    updateReminderPlan(result)
    void loadOverview()
  } catch {
    if (sequence === loadSequence) {
      plan.value = null
      error.value = '计划读取失败，请检查本地服务。'
    }
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

async function loadOverview() {
  const sequence = ++overviewSequence
  if (selectedPeriod.value !== 'day') return
  const start = week.value[0]
  const end = week.value[6]
  try {
    const result = await planRequest<Record<string, DayCounts>>(`/overview?start=${start}&end=${end}`)
    if (sequence === overviewSequence && start === week.value[0]) {
      overview.value = result
      if (plan.value && (plan.value.period || 'day') === 'day') overview.value[plan.value.day] = planCounts(plan.value)
    }
  } catch { /* The calendar dots are optional; the daily plan remains usable. */ }
}

function selectDay(day: string, period: PlanPeriod = selectedPeriod.value) {
  if (busy.value || drag.value || !validDay(day)) return
  closeDialog()
  void router.replace({ query: { ...route.query, date: day, period } })
  void loadDay(day, period)
}
function navigatePeriod(offset: number) {
  const next = selectedPeriod.value === 'day' ? shiftDay(selectedDay.value, offset * 7) : shiftPeriod(selectedPeriod.value, selectedDay.value, offset)
  if (validDay(next)) selectDay(next)
}
function dateChanged(event: Event) {
  const value = (event.target as HTMLInputElement).value
  if (selectedPeriod.value === 'year') {
    const year = Number(value)
    if (Number.isInteger(year) && year >= 1900 && year <= 9998) selectDay(`${year}-01-01`)
  } else selectDay(selectedPeriod.value === 'month' ? `${value}-01` : value)
}
function visibleTasks(section: PlanSection) { return tab.value === 'todo' ? section.tasks.filter(task => !task.done) : section.tasks }
function setScheduleView(value: boolean) {
  if (busy.value || drag.value) return
  void router.replace({ query: { ...route.query, view: value ? 'schedule' : undefined } })
}
function notify(message: string) {
  clearTimeout(toastTimer)
  toast.value = message
  toastTimer = setTimeout(() => { toast.value = '' }, 2500)
}
async function enableReminders() {
  if (reminderPermission.value === 'unsupported') {
    notify('当前浏览器不支持系统通知，页面弹窗提醒仍会正常使用')
    return
  }
  if (reminderPermission.value === 'granted') {
    notify('系统到点提醒已开启，任务到时间会自动提醒')
    return
  }
  if (reminderPermission.value === 'denied') {
    notify('浏览器通知权限已关闭，页面内弹窗提醒仍会正常使用')
    return
  }
  reminderPermission.value = await Notification.requestPermission()
  notify(reminderPermission.value === 'granted'
    ? '系统到点提醒已开启'
    : '未开启系统通知，页面内弹窗提醒仍会正常使用')
}
function reminderStorageKeys() {
  try {
    const raw = localStorage.getItem('smarttodo-reminders-v1')
    const values = raw ? JSON.parse(raw) : []
    return new Set<string>(Array.isArray(values) ? values.filter(value => typeof value === 'string') : [])
  } catch { return new Set<string>() }
}
function saveReminderStorageKeys(keys: Set<string>) {
  try {
    const values = [...keys].slice(-400)
    localStorage.setItem('smarttodo-reminders-v1', JSON.stringify(values))
  } catch { /* Private browsing can disable local storage. */ }
}
function systemNotify(entries: PlannerReminder[]) {
  if (reminderPermission.value !== 'granted' || typeof Notification === 'undefined') return
  const message = entries.length === 1
    ? `${entries[0].sectionTitle} · ${taskTimeLabel(entries[0].task)}  ${entries[0].task.title}`
    : `${entries[0].task.title} 等 ${entries.length} 项任务已到时间`
  try {
    const notification = new Notification('SmartTodo 到点提醒', { body: message, tag: `smarttodo-${todayKey()}` })
    notification.onclick = () => {
      window.focus()
      notification.close()
      if (reminders.value.length) reminderOpen.value = true
    }
  } catch { /* Keep the in-page reminder when system notifications are unavailable. */ }
}
function showPendingReminders() {
  if (document.visibilityState === 'visible' && !dialog.value && !busy.value && !drag.value) reminderOpen.value = reminders.value.length > 0
}
function queueReminders(entries: PlannerReminder[]) {
  const keys = reminderStorageKeys()
  const fresh = entries.filter(entry => {
    const key = reminderKey(todayKey(), entry.task, entry.period)
    if (keys.has(key)) return false
    keys.add(key)
    return true
  })
  if (!fresh.length) return
  saveReminderStorageKeys(keys)
  reminders.value = [...reminders.value, ...fresh].filter((entry, index, all) =>
    all.findIndex(item => reminderKey(todayKey(), item.task, item.period) === reminderKey(todayKey(), entry.task, entry.period)) === index)
  if (document.visibilityState !== 'visible') systemNotify(fresh)
  showPendingReminders()
}
function updateReminderPlan(saved: DailyPlan) {
  const period = saved.period || 'day'
  if (periodBounds(period, todayKey()).start !== saved.day) return
  reminderPlans.value = [...reminderPlans.value.filter(item => !samePlan(item, saved)), saved]
}
async function ensureReminderPlans(): Promise<DailyPlan[]> {
  const day = todayKey()
  if (reminderPlansDay === day && Date.now() - reminderPlansLoadedAt < 30_000) return reminderPlans.value
  if (!reminderPlanRequest) {
    reminderPlanRequest = planRequest<DailyPlan[]>(`/agenda/${day}`)
      .then(result => {
        reminderPlans.value = result.map(item => {
          const cached = reminderPlans.value.find(saved => samePlan(saved, item))
          return cached && (cached.schedule_revision > item.schedule_revision || cached.revision > item.revision) ? cached : item
        })
        reminderPlansLoadedAt = Date.now()
        reminderPlansDay = day
        return reminderPlans.value
      })
      .catch(() => reminderPlans.value)
      .finally(() => { reminderPlanRequest = null })
  }
  return reminderPlanRequest
}
async function checkReminders() {
  if (reminderCheckInProgress) return
  reminderCheckInProgress = true
  const from = reminderLastChecked
  const now = new Date()
  reminderLastChecked = now
  try {
    const activePlans = await ensureReminderPlans()
    const latestNow = new Date()
    queueReminders(activePlans.flatMap(item => dueReminderTasks(item, from, latestNow)))
    showPendingReminders()
  } finally {
    reminderCheckInProgress = false
  }
}
function reminderVisibilityChanged() {
  if (document.visibilityState === 'visible') {
    void checkReminders()
    showPendingReminders()
  }
}
function dismissReminders() {
  reminderOpen.value = false
  reminders.value = []
}
async function openReminderTask(reminder?: PlannerReminder) {
  if (!reminder) return
  const day = todayKey()
  const period = reminder.period || 'day'
  dismissReminders()
  if (selectedDay.value !== day || selectedPeriod.value !== period) {
    void router.replace({ query: { ...route.query, date: day, period } })
    await loadDay(day, period)
  }
  const section = plan.value?.sections.find(item => item.id === reminder.sectionId)
  const task = section?.tasks.find(item => item.id === reminder.task.id)
  if (section && task) openTask(section, task)
}
async function completeReminder(reminder: PlannerReminder) {
  const source = reminderPlans.value.find(item => (item.period || 'day') === (reminder.period || 'day') && item.day === (reminder.planDay || todayKey()))
  if (!source || saving.value) return
  const next = clonePlan(source)
  const task = next.sections.flatMap(section => section.tasks).find(item => item.id === reminder.task.id)
  if (!task) return
  task.done = true
  if (await persistPlan(next, '事项已完成')) {
    reminders.value = reminders.value.filter(item => reminderKey(todayKey(), item.task, item.period) !== reminderKey(todayKey(), reminder.task, reminder.period))
    if (!reminders.value.length) reminderOpen.value = false
  }
}
function openDialog(type: DialogType) {
  if (busy.value || !plan.value) return
  modalError.value = ''
  confirmDelete.value = false
  dialog.value = type
}
function closeDialog() {
  if (saving.value) return
  dialog.value = null
  modalError.value = ''
  confirmDelete.value = false
  window.setTimeout(showPendingReminders, 0)
}

async function persistPlan(next: DailyPlan, message = ''): Promise<boolean> {
  if (!plan.value || saving.value) return false
  const selected = samePlan(plan.value, next)
  const path = planPath(next.period || 'day', next.day)
  const previous = plan.value
  saving.value = true
  error.value = ''
  modalError.value = ''
  if (selected) plan.value = next
  try {
    const saved = await planRequest<DailyPlan>(path, { method: 'PUT', body: JSON.stringify(next) })
    if (selected) plan.value = saved
    updateReminderPlan(saved)
    if ((saved.period || 'day') === 'day') overview.value[next.day] = planCounts(saved)
    void loadOverview()
    if (message) notify(message)
    return true
  } catch (failure) {
    if (selected) plan.value = previous
    let message = '保存失败，改动尚未保存，请重试。'
    if (failure instanceof PlanRequestError && failure.status === 409) {
      message = '其他窗口已更新计划或每日任务，已读取最新版本，请核对后重新保存。'
      try {
        const latest = await planRequest<DailyPlan>(path)
        if (selected) plan.value = latest
        updateReminderPlan(latest)
      } catch { /* Keep the prior version on connection loss. */ }
    }
    error.value = message
    modalError.value = message
    return false
  } finally { saving.value = false }
}
async function persist(next: DailyPlan, message = '') {
  return persistPlan(next, message)
}

function openTitle() {
  dayTitle.value = plan.value?.title || ''
  openDialog('title')
}
async function saveTitle() {
  if (!plan.value) return
  if (!dayTitle.value.trim()) { modalError.value = '请输入计划主题。'; return }
  const next = clonePlan(plan.value)
  next.title = dayTitle.value.trim()
  if (await persist(next, '计划主题已保存')) closeDialog()
}
function openSection(section?: PlanSection) {
  sectionForm.value = section
    ? { id: section.id, title: section.title, color: section.color, start: section.start, end: section.end }
    : { id: '', title: '', color: colors[(plan.value?.sections.length || 0) % colors.length].value, start: '', end: '' }
  deleteMoveTarget.value = plan.value?.sections.find(item => item.id !== section?.id)?.id || ''
  openDialog('section')
}
async function saveSection() {
  if (!plan.value) return
  if (!sectionForm.value.title.trim()) { modalError.value = '请输入宫格主题。'; return }
  if (sectionForm.value.start && sectionForm.value.end && sectionForm.value.start >= sectionForm.value.end) {
    modalError.value = '结束时间需要晚于开始时间。'
    return
  }
  const next = clonePlan(plan.value)
  const section = next.sections.find(item => item.id === sectionForm.value.id)
  if (section) Object.assign(section, sectionForm.value, { title: sectionForm.value.title.trim() })
  else next.sections.push({ ...sectionForm.value, title: sectionForm.value.title.trim(), id: crypto.randomUUID(), tasks: [] })
  if (await persist(next, '宫格已保存')) closeDialog()
}
async function deleteSection() {
  if (!plan.value || plan.value.sections.length <= 1) return
  const next = clonePlan(plan.value)
  const section = next.sections.find(item => item.id === sectionForm.value.id)
  const target = next.sections.find(item => item.id === deleteMoveTarget.value)
  if (!section || !target) return
  target.tasks.push(...section.tasks)
  next.sections = next.sections.filter(item => item.id !== section.id)
  if (await persist(next, '宫格已删除，事项已保留')) closeDialog()
}
async function moveSection(delta: number) {
  if (!plan.value) return
  const next = clonePlan(plan.value)
  const from = sectionPosition.value
  if (from < 0 || from + delta < 0 || from + delta >= next.sections.length) return
  const [section] = next.sections.splice(from, 1)
  next.sections.splice(from + delta, 0, section)
  await persist(next, '宫格顺序已更新')
}
function openTask(section?: PlanSection, task?: PlanTask) {
  taskForm.value = {
    id: task?.id || '', title: task?.title || '', notes: task?.notes || '',
    time: task?.time ?? (selectedPeriod.value === 'day' ? section?.start || '' : ''), endTime: task?.endTime || '',
    scheduledDate: task?.scheduledDate || '',
    kind: task?.kind || 'task', done: task?.done || false, daily: task?.daily || false,
    sectionId: section?.id || plan.value?.sections[0].id || ''
  }
  openDialog('task')
}
function createScheduledTask(value: { date: string; time: string; sectionId: string }) {
  if (busy.value || !plan.value) return
  openTask(plan.value.sections.find(section => section.id === value.sectionId))
  taskForm.value.time = value.time
  taskForm.value.scheduledDate = selectedPeriod.value === 'day' ? '' : value.date
}
async function saveTask() {
  if (!plan.value) return
  if (!taskForm.value.title.trim()) { modalError.value = '请输入事项标题。'; return }
  if (taskDateError.value) {
    taskDateInput.value?.focus()
    return
  }
  if (taskTimeError.value) {
    (taskForm.value.time ? taskEndInput.value : taskStartInput.value)?.focus()
    return
  }
  const next = clonePlan(plan.value)
  const target = next.sections.find(section => section.id === taskForm.value.sectionId)
  if (!target) { modalError.value = '请选择有效的宫格。'; return }
  const { sectionId, ...form } = taskForm.value
  const task: PlanTask = { ...form, id: form.id || crypto.randomUUID(), title: form.title.trim() }
  if (selectedPeriod.value === 'day') delete task.scheduledDate
  else task.daily = false
  const source = next.sections.find(section => section.tasks.some(item => item.id === task.id))
  if (source?.id === target.id) {
    source.tasks[source.tasks.findIndex(item => item.id === task.id)] = task
  } else {
    if (source) source.tasks = source.tasks.filter(item => item.id !== task.id)
    target.tasks.push(task)
  }
  if (await persist(next, form.id ? '事项已保存' : '事项已添加')) closeDialog()
}
async function deleteTask() {
  if (!plan.value) return
  const next = clonePlan(plan.value)
  for (const section of next.sections) section.tasks = section.tasks.filter(task => task.id !== taskForm.value.id)
  if (await persist(next, '事项已删除')) closeDialog()
}
async function toggleTask(id: string) {
  if (!plan.value || saving.value) return
  const next = clonePlan(plan.value)
  const task = next.sections.flatMap(section => section.tasks).find(task => task.id === id)
  if (!task) return
  task.done = !task.done
  await persist(next, task.done ? '又完成了一件事' : '已恢复为待办')
}
async function reorderTask(id: string, delta: number) {
  if (plan.value && !saving.value) await persist(moveTaskBy(plan.value, id, delta), '优先顺序已更新')
}
async function moveEditingTask(delta: number) { await reorderTask(taskForm.value.id, delta) }

type DragState = {
  taskId: string; title: string; pointerId: number; pointerType: string
  startX: number; startY: number; x: number; y: number; active: boolean; waitForHold: boolean
}
const drag = ref<DragState | null>(null)
const dragPreviewStyle = computed(() => ({
  left: `${Math.max(8, Math.min((drag.value?.x || 0) + 12, window.innerWidth - Math.min(240, window.innerWidth * .65) - 8))}px`,
  top: `${Math.max(8, Math.min((drag.value?.y || 0) + (drag.value?.pointerType === 'touch' ? -100 : 16), window.innerHeight - 120))}px`
}))
const dropTarget = ref<{ sectionId: string; beforeId: string | null } | null>(null)
const dropSectionTitle = computed(() => plan.value?.sections.find(section => section.id === dropTarget.value?.sectionId)?.title)
let scrollFrame = 0
let lastScrollTime = 0
let holdTimer: ReturnType<typeof setTimeout> | undefined
let clickTimer: ReturnType<typeof setTimeout> | undefined
let dragElement: HTMLElement | null = null

function startDrag(event: PointerEvent, task: PlanTask) {
  if (busy.value || event.button !== 0 || !event.isPrimary || drag.value || dialog.value) return
  clearClickSuppression()
  const grip = !!(event.target as Element).closest('.task-grip')
  dragElement = event.currentTarget as HTMLElement
  drag.value = {
    taskId: task.id, title: task.title, pointerId: event.pointerId, pointerType: event.pointerType,
    startX: event.clientX, startY: event.clientY, x: event.clientX, y: event.clientY,
    active: false, waitForHold: event.pointerType === 'touch' && !grip
  }
  if (drag.value.waitForHold) holdTimer = setTimeout(activateDrag, 300)
  window.addEventListener('pointermove', trackDrag, { passive: false })
  window.addEventListener('pointerup', finishDrag)
  window.addEventListener('pointercancel', pointerCancelled)
  window.addEventListener('pointerdown', anotherPointer)
  window.addEventListener('touchmove', preventTouchScroll, { passive: false })
  window.addEventListener('contextmenu', preventDragMenu)
  window.addEventListener('blur', cancelDrag)
  window.addEventListener('keydown', dragKey)
  document.addEventListener('visibilitychange', visibilityChanged)
}
function activateDrag() {
  if (!drag.value || drag.value.active || !dragElement?.isConnected) return
  clearTimeout(holdTimer)
  drag.value.active = true
  dragElement.setPointerCapture(drag.value.pointerId)
  window.addEventListener('click', suppressDragClick, true)
  locateDrop()
  lastScrollTime = 0
  scrollFrame = requestAnimationFrame(autoScroll)
}
function suppressDragClick(event: MouseEvent) {
  if (event.detail === 0) return
  event.preventDefault()
  event.stopImmediatePropagation()
  clearClickSuppression()
}
function clearClickSuppression() {
  clearTimeout(clickTimer)
  window.removeEventListener('click', suppressDragClick, true)
  window.removeEventListener('pointerdown', clearClickSuppression, true)
}
function preventTouchScroll(event: TouchEvent) {
  if (drag.value?.active && event.cancelable) event.preventDefault()
}
function preventDragMenu(event: Event) {
  if (drag.value?.pointerType === 'touch') event.preventDefault()
}
function anotherPointer(event: PointerEvent) {
  if (drag.value && event.pointerId !== drag.value.pointerId) cancelDrag()
}
function pointerCancelled(event: PointerEvent) {
  if (event.pointerId === drag.value?.pointerId) cancelDrag()
}
function visibilityChanged() {
  if (document.hidden) cancelDrag()
}
function locateDrop() {
  if (!drag.value) return
  const hit = document.elementFromPoint(drag.value.x, drag.value.y)
  const section = hit?.closest<HTMLElement>('[data-drop-section]')
  if (!section) { dropTarget.value = null; return }
  const rows = Array.from(section.querySelectorAll<HTMLElement>('[data-task-id]')).map(row => {
    const box = row.getBoundingClientRect()
    return { id: row.dataset.taskId!, top: box.top, height: box.height }
  })
  dropTarget.value = { sectionId: section.dataset.dropSection!, beforeId: dropBeforeTask(rows, drag.value.taskId, drag.value.y) }
}
function autoScroll(time: number) {
  if (!drag.value?.active) return
  const navigation = document.querySelector<HTMLElement>('.mobile-nav')?.getBoundingClientRect()
  const bottom = navigation?.height ? navigation.top : window.innerHeight
  const amount = dragScrollSpeed(drag.value.y, 0, bottom)
  const elapsed = lastScrollTime ? Math.min(32, time - lastScrollTime) : 16
  lastScrollTime = time
  if (amount && drag.value.x >= 0 && drag.value.x <= window.innerWidth) {
    window.scrollBy({ top: amount * elapsed / 16, behavior: 'instant' })
  }
  locateDrop()
  scrollFrame = requestAnimationFrame(autoScroll)
}
function trackDrag(event: PointerEvent) {
  if (!drag.value || drag.value.pointerId !== event.pointerId) return
  drag.value.x = event.clientX
  drag.value.y = event.clientY
  const distance = Math.hypot(event.clientX - drag.value.startX, event.clientY - drag.value.startY)
  if (!drag.value.active && distance > (drag.value.waitForHold ? 8 : 6)) {
    if (drag.value.waitForHold) { cancelDrag(); return }
    activateDrag()
  }
  if (drag.value?.active) {
    if (event.cancelable) event.preventDefault()
    locateDrop()
  }
}
function cancelDrag() {
  const current = drag.value
  drag.value = null
  dropTarget.value = null
  clearTimeout(holdTimer)
  cancelAnimationFrame(scrollFrame)
  if (current && dragElement?.hasPointerCapture(current.pointerId)) dragElement.releasePointerCapture(current.pointerId)
  dragElement = null
  if (current?.active) {
    // Consume the click synthesized on release, but never consume a new gesture.
    clickTimer = setTimeout(clearClickSuppression, 500)
    window.addEventListener('pointerdown', clearClickSuppression, true)
  }
  window.removeEventListener('pointermove', trackDrag)
  window.removeEventListener('pointerup', finishDrag)
  window.removeEventListener('pointercancel', pointerCancelled)
  window.removeEventListener('pointerdown', anotherPointer)
  window.removeEventListener('touchmove', preventTouchScroll)
  window.removeEventListener('contextmenu', preventDragMenu)
  window.removeEventListener('blur', cancelDrag)
  window.removeEventListener('keydown', dragKey)
  document.removeEventListener('visibilitychange', visibilityChanged)
}
function dragKey(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); cancelDrag() }
}
function finishDrag(event: PointerEvent) {
  if (!drag.value || event.pointerId !== drag.value.pointerId) return
  drag.value.x = event.clientX
  drag.value.y = event.clientY
  if (drag.value.active) locateDrop()
  const current = drag.value
  const target = dropTarget.value
  cancelDrag()
  if (current.active && target && plan.value) {
    const next = moveTask(plan.value, current.taskId, target.sectionId, target.beforeId)
    const source = plan.value.sections.find(section => section.tasks.some(task => task.id === current.taskId))
    const destination = next.sections.find(section => section.id === target.sectionId)
    if (JSON.stringify(next) !== JSON.stringify(plan.value)) {
      void persist(next, source?.id === target.sectionId ? '优先顺序已更新' : `已移至「${destination?.title}」`)
    }
  }
}
function beforeUnload(event: BeforeUnloadEvent) {
  if (saving.value) { event.preventDefault(); event.returnValue = '' }
}
watch(() => [route.query.date, route.query.period], () => {
  const day = validDay(route.query.date) ? route.query.date : todayKey()
  const period = validPeriod(route.query.period) ? route.query.period : 'day'
  if (day !== selectedDay.value || period !== selectedPeriod.value) {
    closeDialog()
    void loadDay(day, period)
  }
})
onMounted(() => {
  void loadDay(selectedDay.value)
  window.addEventListener('beforeunload', beforeUnload)
  document.addEventListener('visibilitychange', reminderVisibilityChanged)
  reminderTimer = window.setInterval(() => { void checkReminders() }, 15_000)
  void checkReminders()
})
onBeforeUnmount(() => {
  ++loadSequence
  ++overviewSequence
  clearTimeout(toastTimer)
  if (reminderTimer !== undefined) window.clearInterval(reminderTimer)
  document.removeEventListener('visibilitychange', reminderVisibilityChanged)
  cancelDrag()
  clearClickSuppression()
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<style src="@/components/planner/planner.css"></style>
