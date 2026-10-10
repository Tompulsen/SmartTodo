<template>
  <dialog ref="dialog" class="planner-dialog" :aria-label="title" @cancel.prevent="$emit('close')"
    @click="outside">
    <div class="dialog-content">
      <header class="dialog-heading">
        <h2>{{ title }}</h2>
        <button class="icon-button" type="button" aria-label="关闭窗口" title="关闭窗口" :disabled="busy" @click="$emit('close')">
          <PlannerIcon name="close" />
        </button>
      </header>
      <slot />
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import PlannerIcon from './PlannerIcon.vue'
const props = defineProps<{ open: boolean; title: string; busy?: boolean }>()
const emit = defineEmits<{ (event: 'close'): void }>()
const dialog = ref<HTMLDialogElement>()
watch(() => props.open, async (open) => {
  await nextTick()
  if (open && !dialog.value?.open) dialog.value?.showModal()
  else if (!open && dialog.value?.open) dialog.value.close()
}, { immediate: true })
function outside(event: MouseEvent) {
  if (event.target === dialog.value && !props.busy) emit('close')
}
</script>
