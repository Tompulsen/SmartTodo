<template>
  <li class="plan-task" :class="{ 'is-done': task.done, 'is-dragging': dragging, 'drop-before': dropBefore }"
    :data-task-id="task.id" @pointerdown="startDrag" @dragstart.prevent>
    <button class="task-grip" type="button" :aria-label="`拖动排序：${task.title}`" title="拖动排序；也可用上下方向键"
      :disabled="busy"
      @keydown.up.prevent="$emit('move', task.id, -1)" @keydown.down.prevent="$emit('move', task.id, 1)">
      <PlannerIcon name="grip" />
    </button>
    <input class="task-checkbox" type="checkbox" :checked="task.done" :disabled="busy"
      :aria-label="`完成：${task.title}`" @change="$emit('toggle', task.id)" />
    <button type="button" class="task-body" :disabled="busy" @click="$emit('edit', task)">
      <span class="task-title">{{ task.title }}</span>
      <span class="task-meta">
        <PlannerIcon :name="task.kind === 'event' ? 'note' : 'clock'" />
        <span v-if="period !== 'day' && task.scheduledDate" class="task-date">{{ task.scheduledDate.replace(/-/g, '.') }}</span>
        <span class="task-time"><span>{{ task.time || (period !== 'day' && !task.scheduledDate ? '本期内完成' : '全天') }}</span><span v-if="task.time && task.endTime">～{{ task.endTime }}</span></span>
        <span v-if="task.kind === 'event'" class="event-tag">事项</span>
        <span v-if="task.daily" class="daily-tag"><PlannerIcon name="repeat" />每日</span>
        <span v-if="task.notes" class="notes-dot" title="含备注"></span>
      </span>
    </button>
    <span class="task-rank" :title="`优先顺序 ${rank}`">{{ String(rank).padStart(2, '0') }}</span>
    <button class="task-edit" type="button" :aria-label="`编辑：${task.title}`" title="编辑事项" :disabled="busy"
      @click="$emit('edit', task)"><PlannerIcon name="more" /></button>
  </li>
</template>

<script setup lang="ts">
import PlannerIcon from './PlannerIcon.vue'
import type { PlanTask, PlanPeriod } from './planner'
const props = withDefaults(defineProps<{ task: PlanTask; period?: PlanPeriod; rank: number; busy: boolean; dragging: boolean; dropBefore: boolean }>(), { period: 'day' })
const emit = defineEmits<{
  (event: 'drag', pointer: PointerEvent, task: PlanTask): void
  (event: 'toggle', id: string): void
  (event: 'edit', task: PlanTask): void
  (event: 'move', id: string, delta: number): void
}>()
function startDrag(event: PointerEvent) {
  if (props.busy || (event.target as Element).closest('.task-checkbox, .task-edit')) return
  emit('drag', event, props.task)
}
</script>
