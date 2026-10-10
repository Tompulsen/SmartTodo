<template>
  <div class="schedule-task" :class="[`color-${entry.section.color}`, { 'schedule-done': entry.task.done }]">
    <label class="schedule-check">
      <input class="task-checkbox" type="checkbox" :checked="entry.task.done" :disabled="busy"
        :aria-label="`完成：${entry.task.title}`" @change="$emit('toggle', entry.task.id)" />
    </label>
    <button class="schedule-task-open" :disabled="busy" :aria-label="`编辑：${entry.task.title}`" @click="$emit('edit', entry)">
      <strong>{{ entry.task.title }}</strong>
      <span><time v-if="showDate && entry.date">{{ entry.date.slice(5).replace('-', '/') }}</time>
        <span>{{ taskTimeLabel(entry.task) }}</span><span>{{ entry.section.title }}</span>
        <span v-if="entry.task.daily"><PlannerIcon name="repeat" /> 每日</span>
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import PlannerIcon from './PlannerIcon.vue'
import { taskTimeLabel, type ScheduleEntry } from './planner'
defineProps<{ entry: ScheduleEntry; busy: boolean; showDate?: boolean }>()
defineEmits<{ edit: [entry: ScheduleEntry]; toggle: [id: string] }>()
</script>
