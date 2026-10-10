<template>
  <router-view :key="$route.path === '/index' ? $route.path : $route.fullPath"></router-view>
  <ReminderCenter />
</template>

<script lang="ts">
import ReminderCenter from '@/components/planner/ReminderCenter.vue'
export default {
  name: 'App',
  components: {
    ReminderCenter
  }
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-size: 16px;
  background: #CDCDCD;
}
</style>
