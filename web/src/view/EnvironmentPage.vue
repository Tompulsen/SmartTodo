<template>
  <main class="account-screen environment-screen">
    <div class="account-content environment-content">
      <header class="account-topbar">
        <router-link to="/index" class="account-brand">SmartTodo<span>.</span></router-link>
        <router-link to="/tools" class="account-back"><PlannerIcon name="back" />工具箱</router-link>
      </header>
      <div class="account-heading">
        <div><p class="account-eyebrow">工作与生活 / 今日天气</p><h1>环境舒适度</h1></div>
        <span class="environment-date">{{ weather ? weatherTime(weather.current.time, weather.timezone, true) : today }}</span>
      </div>

      <section v-if="!locationSharing.active || !locationSharing.position" class="environment-entry" aria-labelledby="location-entry-title">
        <span class="environment-entry-icon"><PlannerIcon name="locate" /></span>
        <h2 id="location-entry-title">从当前位置，了解今天的天气</h2>
        <p>{{ auth.localMode ? '使用环境舒适度需要设备定位，以获取当前位置的天气和体感。' : '使用环境舒适度需要设备定位，并在使用期间向平台管理员共享当前位置。' }}</p>
        <ul>
          <li>天气查询会向 Open-Meteo 提供约 1 公里精度的坐标。</li>
          <li v-if="!auth.localMode">管理员可查看设备上报的坐标、定位精度与更新时间，仅保留最新一次位置。</li>
          <li>{{ auth.localMode ? '本地模式不向平台管理员上传位置。' : '离开此页面会停止定位并结束共享；切到后台或锁屏时，位置更新可能暂停。' }}</li>
        </ul>
        <p v-if="locationSharing.error" class="account-error" role="alert">{{ locationSharing.error }}</p>
        <button type="button" class="account-primary environment-enter" :disabled="locationSharing.busy" @click="beginLocationSession">
          <PlannerIcon :name="locationSharing.busy ? 'refresh' : 'location'" />
          {{ locationSharing.busy ? '正在获取位置…' : '同意定位并使用' }}
        </button>
        <router-link to="/tools" class="environment-later">返回工具箱</router-link>
      </section>

      <template v-else>
        <div class="environment-location" role="status">
          <div><PlannerIcon name="location" /><strong>当前位置</strong><span>精度约 {{ reading(locationSharing.position.coords.accuracy) }} 米</span></div>
          <span class="environment-sharing"><PlannerIcon name="shield" />{{ auth.localMode ? '本地定位' : '使用期间向管理员共享位置' }}</span>
        </div>
        <p v-if="error" class="account-error" role="alert">{{ error }}</p>
        <div v-if="loading && !weather" class="environment-loading" role="status"><PlannerIcon name="cloud-sun" /><p>正在读取当前位置的天气…</p></div>
        <button v-if="!weather && !loading" type="button" class="account-secondary" @click="loadWeather"><PlannerIcon name="refresh" />重新读取天气</button>
        <template v-if="weather">
          <section class="environment-current" aria-label="当前天气">
            <div class="weather-overview">
              <p class="weather-place">{{ weather.timezone.replace(/_/g, ' ') }} <span>{{ weatherTime(weather.current.time, weather.timezone) }} 更新</span></p>
              <div class="weather-temperature"><PlannerIcon :name="condition.icon" /><strong>{{ reading(weather.current.temperature_2m) }}<span>°C</span></strong></div>
              <div class="weather-description"><h2>{{ condition.label }}</h2><span>{{ reading(weather.daily.temperature_2m_min) }}° / {{ reading(weather.daily.temperature_2m_max) }}°</span></div>
            </div>
            <div class="weather-comfort" :data-tone="feeling?.tone">
              <p class="account-eyebrow"><PlannerIcon name="leaf" /> 当前体感</p>
              <h2>{{ feeling?.label }}</h2><p>{{ feeling?.detail }}</p>
              <span>室外天气参考，非室内实测</span>
            </div>
          </section>
          <section class="weather-metrics" aria-label="天气指标">
            <div><PlannerIcon name="temperature" /><span>体感温度</span><strong>{{ reading(weather.current.apparent_temperature) }}<small>°C</small></strong></div>
            <div><PlannerIcon name="humidity" /><span>相对湿度</span><strong>{{ reading(weather.current.relative_humidity_2m) }}<small>%</small></strong></div>
            <div><PlannerIcon name="wind" /><span>当前风速</span><strong>{{ reading(weather.current.wind_speed_10m, 1) }}<small>m/s</small></strong></div>
            <div><PlannerIcon name="rain" /><span>今日降水概率</span><strong>{{ reading(weather.daily.precipitation_probability_max) }}<small>%</small></strong></div>
          </section>
          <section class="weather-hourly" aria-labelledby="hourly-title">
            <header class="weather-section-heading"><div><p class="account-eyebrow">按所在地时间</p><h2 id="hourly-title">今日逐小时天气</h2></div><button type="button" class="account-secondary weather-refresh" :disabled="loading" @click="loadWeather"><PlannerIcon name="refresh" />{{ loading ? '更新中' : '刷新' }}</button></header>
            <div ref="hourlyTable" class="weather-table-wrap" tabindex="0" aria-label="可横向滚动的今日天气表">
              <table class="weather-table">
                <thead><tr><th scope="col">时间</th><th v-for="hour in weather.hourly" :key="hour.time!" scope="col" :class="{ 'is-current': isCurrentHour(hour.time) }">{{ weatherTime(hour.time, weather.timezone) }}</th></tr></thead>
                <tbody>
                  <tr><th scope="row">天气</th><td v-for="hour in weather.hourly" :key="hour.time!"><PlannerIcon :name="weatherCondition(hour.weather_code, isDay(hour.time)).icon" /><span>{{ weatherCondition(hour.weather_code, isDay(hour.time)).label }}</span></td></tr>
                  <tr><th scope="row">温度</th><td v-for="hour in weather.hourly" :key="hour.time!">{{ reading(hour.temperature_2m) }}°</td></tr>
                  <tr><th scope="row">降水概率</th><td v-for="hour in weather.hourly" :key="hour.time!" class="weather-rain">{{ reading(hour.precipitation_probability) }}%</td></tr>
                  <tr><th scope="row">风速</th><td v-for="hour in weather.hourly" :key="hour.time!">{{ reading(hour.wind_speed_10m, 1) }} <small>m/s</small></td></tr>
                </tbody>
              </table>
            </div>
          </section>
          <section class="weather-daylight" aria-label="今日补充信息">
            <div><PlannerIcon name="sun" /><span>日出 <strong>{{ weatherTime(weather.daily.sunrise, weather.timezone) }}</strong></span></div>
            <div><PlannerIcon name="moon" /><span>日落 <strong>{{ weatherTime(weather.daily.sunset, weather.timezone) }}</strong></span></div>
            <div><PlannerIcon name="sun" /><span>最高紫外线指数 <strong>{{ reading(weather.daily.uv_index_max, 1) }}</strong></span></div>
          </section>
          <footer class="weather-footer"><span>天气数据由 <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> 提供</span><span>预报可能与实际天气有差异</span></footer>
        </template>
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { auth, authRequest } from '@/auth'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import { beginLocationSession, endLocationSession, locationSharing } from '@/components/environment/location-sharing'
import { comfort, reading, weatherCondition, weatherTime, type WeatherReply } from '@/components/environment/weather'

const weather = ref<WeatherReply | null>(null)
const loading = ref(false)
const error = ref('')
const hourlyTable = ref<HTMLElement>()
const today = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const condition = computed(() => weatherCondition(weather.value?.current.weather_code ?? null, weather.value?.current.is_day !== 0))
const feeling = computed(() => weather.value ? comfort(weather.value.current) : null)
let requestVersion = 0
let refreshTimer: ReturnType<typeof setInterval> | null = null
let lastRefresh = 0
const coordinates = computed(() => {
  const position = locationSharing.position
  return position ? `${position.coords.latitude.toFixed(2)},${position.coords.longitude.toFixed(2)}` : ''
})
function isCurrentHour(time: number | null) {
  const current = weather.value?.current.time
  return time !== null && current != null && time <= current && current < time + 3600
}
function isDay(time: number | null) {
  const day = weather.value?.daily
  return time !== null && day?.sunrise != null && day.sunset != null && time >= day.sunrise && time < day.sunset
}
function scrollCurrentHour() {
  const table = hourlyTable.value
  const currentHour = table?.querySelector<HTMLElement>('th.is-current')
  if (table && currentHour) table.scrollLeft = Math.max(0, table.scrollLeft + currentHour.getBoundingClientRect().left - table.getBoundingClientRect().left - 172)
}
async function loadWeather() {
  const position = locationSharing.position
  if (!locationSharing.active || !position || loading.value || document.hidden) return
  const version = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const result = await authRequest<WeatherReply>('/api/environment/weather', 'POST', {
      latitude: position.coords.latitude, longitude: position.coords.longitude
    })
    if (version === requestVersion && locationSharing.active) {
      const firstLoad = weather.value === null
      weather.value = result
      lastRefresh = Date.now()
      if (firstLoad) {
        await nextTick()
        scrollCurrentHour()
      }
    }
  } catch (failure) {
    if (version === requestVersion) error.value = failure instanceof Error ? failure.message : '天气读取失败，请重试。'
  } finally { if (version === requestVersion) loading.value = false }
}
watch(coordinates, () => {
  ++requestVersion
  weather.value = null
  loading.value = false
  error.value = ''
  if (coordinates.value) void loadWeather()
})
function refreshIfNeeded() {
  if (locationSharing.active && !document.hidden && Date.now() - lastRefresh > 300000) void loadWeather()
}
onMounted(() => {
  refreshTimer = setInterval(refreshIfNeeded, 60000)
  document.addEventListener('visibilitychange', refreshIfNeeded)
  window.addEventListener('resize', scrollCurrentHour)
})
onUnmounted(() => {
  ++requestVersion
  if (refreshTimer) clearInterval(refreshTimer)
  document.removeEventListener('visibilitychange', refreshIfNeeded)
  window.removeEventListener('resize', scrollCurrentHour)
  endLocationSession()
})
</script>

<style src="@/components/account/account.css"></style>
<style scoped>
.environment-content { max-width: 1100px; }
.environment-date { font-size: 13px; color: #5e7167; text-align: right; }
.environment-entry { max-width: 640px; margin: 36px auto; padding: 36px 0; border-top: 1px solid #d4dfd8; }
.environment-entry-icon { width: 56px; height: 56px; display: grid; place-items: center; font-size: 26px; background: #e4eff2; color: #2b7380; border-radius: 8px; margin-bottom: 24px; }
.environment-entry h2 { font-size: 22px; line-height: 1.5; }
.environment-entry > p { color: #496155; margin: 16px 0; }
.environment-entry ul { padding-left: 22px; color: #617369; font-size: 14px; display: grid; gap: 12px; margin: 24px 0; }
.environment-entry .account-error { color: #a03831; }
.environment-enter { margin-top: 10px; }
.environment-later { display: inline-flex; padding: 12px 18px; margin-left: 8px; color: #617369; font-size: 14px; }
.environment-location { border-block: 1px solid #dbe3df; padding: 14px 0; display: flex; align-items: center; justify-content: space-between; gap: 12px 24px; flex-wrap: wrap; font-size: 12px; color: #53695e; }
.environment-location > div { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.environment-location strong { font-size: 14px; color: #293b33; }
.environment-sharing { display: inline-flex; align-items: center; gap: 8px; color: #2a6f75; }
.environment-current { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center; padding: 32px 0; }
.weather-place { margin: 0 0 16px; font-size: 14px; color: #4a6155; overflow-wrap: anywhere; }
.weather-place span { color: #687b70; font-size: 12px; margin-left: 16px; }
.weather-temperature { display: flex; align-items: center; gap: 28px; }
.weather-temperature > svg { color: #d9a52a; font-size: 66px; width: 90px; }
.weather-temperature strong { font-size: 68px; font-weight: 500; line-height: 1.2; font-variant-numeric: tabular-nums; }
.weather-temperature strong span { font-size: 24px; vertical-align: top; display: inline-block; margin: 12px 0 0 5px; color: #5f7367; }
.weather-description { display: flex; align-items: center; gap: 20px; margin-top: 14px; color: #50675a; }
.weather-description h2 { font-size: 18px; }
.weather-description span { font-size: 14px; }
.weather-comfort { padding: 8px 0 8px 32px; border-left: 3px solid #7d9f85; }
.weather-comfort[data-tone="cool"] { border-color: #7ba6ba; }
.weather-comfort[data-tone="warm"] { border-color: #df9c78; }
.weather-comfort h2 { font-size: 26px; margin: 8px 0; }
.weather-comfort p:not(.account-eyebrow) { color: #53695e; margin: 0 0 12px; max-width: 350px; font-size: 14px; }
.weather-comfort > span { color: #728277; font-size: 12px; }
.weather-comfort .account-eyebrow { display: flex; align-items: center; gap: 8px; }
.weather-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-block: 1px solid #dbe3df; }
.weather-metrics > div { padding: 22px; position: relative; border-right: 1px solid #dbe3df; }
.weather-metrics > div:first-child { padding-left: 0; }
.weather-metrics > div:last-child { border-right: 0; }
.weather-metrics > div > svg { color: #56899b; margin-right: 8px; font-size: 14px; }
.weather-metrics > div:nth-child(2) > svg { color: #658e7c; }
.weather-metrics > div > span { color: #63776a; font-size: 12px; }
.weather-metrics strong { display: block; font-size: 28px; font-weight: 500; margin-top: 6px; font-variant-numeric: tabular-nums; }
.weather-metrics small { margin-left: 6px; color: #63776a; font-size: 13px; }
.weather-hourly { padding-top: 28px; }
.weather-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.weather-refresh { font-size: 13px; padding: 8px 14px; }
.weather-table-wrap { overflow-x: auto; max-width: 100%; border: 1px solid #dbe3df; border-radius: 6px; background: #fff; }
.weather-table { border-collapse: separate; border-spacing: 0; font-size: 13px; text-align: center; width: max-content; min-width: 100%; }
.weather-table th, .weather-table td { min-width: 80px; padding: 12px 10px; border-bottom: 1px solid #edf1ef; }
.weather-table th { font-weight: 500; font-size: 12px; color: #5e7266; background: #f4f7f5; }
.weather-table tr > :first-child { position: sticky; left: 0; min-width: 92px; border-right: 1px solid #e1e7e3; z-index: 1; }
.weather-table thead th.is-current { background: #fce7e2; color: #8e473d; }
.weather-table td > svg { display: block; color: #a88733; font-size: 20px; margin: 0 auto 8px; }
.weather-table td > span { font-size: 11px; color: #66796e; white-space: nowrap; }
.weather-table small { font-size: 10px; color: #6e8074; }
.weather-table tr:last-child > * { border-bottom: 0; }
.weather-rain { color: #357f95; }
.weather-daylight { padding: 24px 0; display: flex; gap: 24px 40px; flex-wrap: wrap; border-bottom: 1px solid #dbe3df; }
.weather-daylight > div { display: flex; align-items: center; gap: 10px; color: #687c70; font-size: 12px; }
.weather-daylight svg { color: #a17a34; }
.weather-daylight strong { font-weight: 500; color: #374e40; margin-left: 10px; }
.weather-footer { display: flex; gap: 10px 24px; justify-content: space-between; flex-wrap: wrap; padding: 20px 0; font-size: 11px; color: #667a6d; }
.weather-footer a { text-decoration: underline; text-underline-offset: 3px; }
.environment-loading { text-align: center; color: #647a6d; padding: 70px 0; }
.environment-loading > svg { font-size: 44px; color: #c09a45; }
@media (max-width: 640px) {
  .environment-date { max-width: 95px; font-size: 12px; }
  .environment-entry { margin-top: 12px; padding-top: 26px; }
  .environment-entry h2 { font-size: 20px; }
  .environment-enter { width: 100%; }
  .environment-later { display: flex; justify-content: center; margin-left: 0; }
  .environment-current { grid-template-columns: minmax(0, 1fr); gap: 28px; padding: 26px 0; }
  .weather-temperature strong { font-size: 60px; }
  .weather-temperature > svg { width: 74px; font-size: 56px; }
  .weather-comfort { padding-left: 18px; }
  .weather-comfort h2 { font-size: 22px; }
  .weather-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .weather-metrics > div { padding: 18px 16px; }
  .weather-metrics > div:nth-child(odd) { padding-left: 0; }
  .weather-metrics > div:nth-child(even) { border-right: 0; }
  .weather-metrics > div:nth-child(-n+2) { border-bottom: 1px solid #dbe3df; }
  .weather-daylight { gap: 14px; justify-content: space-between; }
}
</style>
