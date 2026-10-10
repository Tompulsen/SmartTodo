<template>
  <div class="reminder-preferences">
    <div class="reminder-setting"><div><strong>页面弹窗</strong><p>按任务的开始时间提醒</p></div><span class="reminder-status">已开启</span></div>
    <div class="reminder-setting"><div><strong>{{ state.native ? '安卓系统通知' : '系统通知' }}</strong><p>{{ permissionLabel }}</p></div>
      <button class="reminder-button" :disabled="state.enabling" @click="enableSystemReminders"><PlannerIcon name="bell" />{{ state.enabling ? '处理中' : state.permission === 'granted' ? '检查权限' : '开启通知' }}</button>
    </div>
    <div v-if="state.native" class="reminder-setting"><div><strong>后台定时提醒</strong>
      <p v-if="!state.nativeReady">需要使用更新后的打包模板重新生成 APK。</p>
      <p v-else>{{ state.nativeCount }} 项已交给手机系统 · 未来 7 天</p>
      <p v-if="state.nativeReady && !state.exact">未允许精确闹钟，提醒可能延迟。</p></div>
      <button v-if="state.nativeReady && !state.exact" class="reminder-button" @click="openExactAlarmSettings">允许准时提醒</button>
    </div>
    <div class="reminder-setting"><label :for="soundId"><strong>页面提示音</strong><p>在页面弹窗时播放短提示音</p></label>
      <input :id="soundId" type="checkbox" role="switch" :checked="state.sound" @change="setReminderSound(($event.target as HTMLInputElement).checked)" />
    </div>
    <p v-if="state.next" class="reminder-next"><PlannerIcon name="clock" />下一项：{{ state.next.task.time }} · {{ state.next.task.title }}</p>
    <p v-if="state.snoozed.length" class="reminder-next">{{ state.snoozed.length }} 项将在延后时间再次提醒</p>
    <p v-if="state.error || state.deliveryError" class="reminder-warning" role="alert">{{ state.error || state.deliveryError }}</p>
    <p v-if="state.notice" class="reminder-notice" role="status">{{ state.notice }}</p>
    <p v-if="!state.storageAvailable" class="reminder-warning">浏览器无法保存提醒状态，刷新后可能再次提示。</p>
    <div class="reminder-preference-actions">
      <button class="reminder-button reminder-primary" :disabled="state.testing" @click="testReminder"><PlannerIcon name="play" />测试提醒</button>
      <button v-if="state.pending.length" class="reminder-button" @click="showPending"><PlannerIcon name="tasks" />待处理 {{ state.pending.length }}</button>
    </div>
    <p class="reminder-footnote">{{ state.nativeReady
      ? '打开应用会更新未来 7 天的提醒。其他设备修改的任务，需要本机联网同步；强行停止应用后请重新打开。'
      : '浏览器关闭、手机锁屏或网页被系统暂停时，无法保证准时提醒。返回页面后会补回当天未处理的提醒。' }}</p>
  </div>
</template>
<script setup lang="ts">
import { computed, getCurrentInstance } from 'vue'
import PlannerIcon from './PlannerIcon.vue'
import { reminderState as state, enableSystemReminders, testReminder, setReminderSound, expandReminder, openExactAlarmSettings } from './reminders'
const permissionLabel = computed(() => ({
  granted: '已允许，请确认系统未开启勿扰模式', denied: '已被阻止，请到系统或网站权限中允许通知',
  default: '尚未授权', unsupported: '当前环境不支持系统通知'
}[state.permission]))
const soundId = `reminder-sound-${getCurrentInstance()?.uid}`
function showPending() { state.settingsOpen = false; expandReminder() }
</script>
