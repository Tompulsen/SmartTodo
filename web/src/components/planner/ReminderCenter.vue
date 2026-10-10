<template>
  <Teleport to="body">
    <button v-if="state.owner && state.pending.length && !state.open && !state.testOpen" class="reminder-floating" @click="showPending">
      <PlannerIcon name="bell" /><span>{{ state.pending.length }} 项待提醒</span>
    </button>
    <dialog ref="popup" class="global-reminder-dialog" aria-labelledby="due-reminder-title" @cancel.prevent="collapseReminder">
      <header class="reminder-header"><span class="reminder-symbol"><PlannerIcon name="bell" /></span>
        <div><p class="reminder-eyebrow">SMARTTODO · {{ state.testOpen ? '测试' : '计划' }}</p><h2 id="due-reminder-title">{{ state.testOpen ? '提醒已准备好' : '到时间了' }}</h2></div>
        <button class="reminder-icon" title="收起提醒" aria-label="收起提醒" @click="collapseReminder"><PlannerIcon name="minus" /></button>
      </header>
      <template v-if="state.testOpen">
        <div class="reminder-test"><strong>给重要的事，留一点时间</strong><p>这是测试弹窗，不会更改你的任务。</p></div>
        <p class="reminder-notice" role="status">{{ state.notice || '正在发送测试通知…' }}</p>
        <footer class="reminder-footer"><button class="reminder-button reminder-primary" autofocus @click="closeTest">测试完成</button></footer>
      </template>
      <template v-else>
        <p class="reminder-description">{{ state.pending.length }} 项待办等待处理，按开始时间排列</p>
        <ul class="reminder-items">
          <li v-for="item in state.pending" :key="item.key">
            <div class="reminder-time"><PlannerIcon name="clock" />{{ taskTimeLabel(item.task) }}<span>{{ item.day.slice(5).replace('-', '/') }} · {{ periodLabels[item.period] }}</span></div>
            <h3>{{ item.task.title }}</h3><p class="reminder-section">{{ item.sectionTitle }}</p>
            <div class="reminder-item-actions">
              <button class="reminder-button" @click="viewTask(item)"><PlannerIcon name="eye" />查看任务</button>
              <button class="reminder-button" @click="reminderAction([item], 'snooze')"><PlannerIcon name="clock" />5 分钟后</button>
              <button class="reminder-icon reminder-complete" :disabled="!!state.busyKey" title="标记完成" aria-label="标记完成" @click="completeReminder(item)"><PlannerIcon name="check" /></button>
            </div>
          </li>
        </ul>
        <p v-if="state.error || state.deliveryError" class="reminder-warning" role="alert">{{ state.error || state.deliveryError }}</p>
        <footer class="reminder-footer"><button class="reminder-button" @click="openReminderCenter"><PlannerIcon name="settings" />提醒设置</button>
          <button class="reminder-button reminder-primary" @click="reminderAction([...state.pending], 'dismiss')">本次不再提醒</button>
        </footer>
      </template>
    </dialog>
    <dialog ref="settings" class="global-reminder-dialog" aria-labelledby="reminder-settings-title" @cancel.prevent="closeSettings">
      <header class="reminder-header"><span class="reminder-symbol"><PlannerIcon name="bell" /></span><div><p class="reminder-eyebrow">SMARTTODO</p><h2 id="reminder-settings-title">提醒中心</h2></div>
        <button class="reminder-icon" aria-label="关闭提醒设置" title="关闭" @click="closeSettings"><PlannerIcon name="close" /></button>
      </header>
      <ReminderPreferences />
    </dialog>
  </Teleport>
</template>
<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import PlannerIcon from './PlannerIcon.vue'
import ReminderPreferences from './ReminderPreferences.vue'
import { taskTimeLabel } from './planner'
import { reminderHref, type ReminderOccurrence } from './reminder-state'
import { reminderState as state, startReminders, stopReminders, collapseReminder, expandReminder, maybeOpenReminder, openReminderCenter, reminderAction, completeReminder } from './reminders'
const router = useRouter()
const popup = ref<HTMLDialogElement>()
const settings = ref<HTMLDialogElement>()
const periodLabels = { day: '日计划', week: '周计划', month: '月计划', year: '年计划' }
function closeSettings() { state.settingsOpen = false; maybeOpenReminder() }
function closeTest() { state.testOpen = false; state.settingsOpen = true }
function showPending() { state.settingsOpen = false; expandReminder() }
async function viewTask(item: ReminderOccurrence) {
  await reminderAction([item], 'dismiss')
  collapseReminder()
  await router.push(reminderHref(item))
}
function navigate(event: Event) {
  const href = (event as CustomEvent).detail
  if (typeof href !== 'string' || !/^\/index(?:\?|$)/.test(href)) return
  collapseReminder()
  state.settingsOpen = false
  void router.push(href)
}
watch(() => [state.open, state.testOpen, state.settingsOpen, state.owner], async () => {
  await nextTick()
  const showPopup = !!state.owner && (state.open || state.testOpen) && !state.settingsOpen
  if (!showPopup) popup.value?.close()
  if (!state.settingsOpen || !state.owner) settings.value?.close()
  if (showPopup && !popup.value?.open) popup.value?.showModal()
  if (state.owner && state.settingsOpen && !settings.value?.open) settings.value?.showModal()
})
onMounted(() => { startReminders(); window.addEventListener('reminder-navigate', navigate) })
onBeforeUnmount(() => { stopReminders(); window.removeEventListener('reminder-navigate', navigate) })
</script>
<style src="./reminders.css"></style>
