<template><FontAwesomeIcon :icon="icons[name] || faCircle" aria-hidden="true" /></template>

<script setup lang="ts">
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
  faCalendarDays, faListCheck, faTableCellsLarge, faClock, faChartColumn, faEllipsis,
  faPlus, faXmark, faPen, faGripVertical, faChevronLeft, faChevronRight, faCheck,
  faArrowUp, faArrowDown, faTrashCan, faSliders, faBars, faHouse, faArrowLeft,
  faCircle, faRotateRight, faCloudArrowDown, faNoteSticky, faBullseye, faCircleCheck, faRepeat,
  faBell, faBellSlash, faPlay, faPause, faStop, faLeaf, faVolumeHigh, faVolumeXmark, faLink, faMinus,
  faMusic, faArrowUpFromBracket, faPowerOff
} from '@fortawesome/free-solid-svg-icons'
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core'

defineProps<{ name: string }>()
const icons: Record<string, IconDefinition> = {
  calendar: faCalendarDays, tasks: faListCheck, grid: faTableCellsLarge, clock: faClock,
  chart: faChartColumn, more: faEllipsis, plus: faPlus, close: faXmark, edit: faPen,
  grip: faGripVertical, left: faChevronLeft, right: faChevronRight, check: faCheck,
  up: faArrowUp, down: faArrowDown, delete: faTrashCan, settings: faSliders, list: faBars,
  home: faHouse, back: faArrowLeft, refresh: faRotateRight, saved: faCloudArrowDown,
  note: faNoteSticky, focus: faBullseye, complete: faCircleCheck, repeat: faRepeat,
  bell: faBell, 'bell-slash': faBellSlash, play: faPlay, pause: faPause, stop: faStop,
  leaf: faLeaf, sound: faVolumeHigh, mute: faVolumeXmark, link: faLink, minus: faMinus,
  music: faMusic, upload: faArrowUpFromBracket, power: faPowerOff
}
</script>
