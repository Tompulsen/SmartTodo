<template>
  <main class="account-screen admin-screen">
    <div class="account-content">
      <header class="account-topbar">
        <router-link to="/index" class="account-brand">SmartTodo<span>.</span></router-link>
        <router-link to="/tools" class="account-back"><PlannerIcon name="back" />工具箱</router-link>
      </header>
      <div class="account-heading">
        <div><p class="account-eyebrow admin-eyebrow">管理员</p><h1>管理控制台</h1></div>
        <span class="account-mode"><PlannerIcon name="shield" /> 用户管理</span>
      </div>
      <p v-if="notice" class="account-notice" role="status">{{ notice }}</p>
      <p v-if="error" class="account-error" role="alert">{{ error }}</p>
      <form class="admin-toolbar" @submit.prevent="searchUsers">
        <label class="account-field admin-search">搜索用户
          <input v-model="query" type="search" maxlength="40" placeholder="账号或昵称" :disabled="loading" />
        </label>
        <label class="account-field">角色
          <select v-model="role" aria-label="角色" :disabled="loading" @change="searchUsers"><option value="all">全部角色</option><option value="admin">管理员</option><option value="user">普通用户</option></select>
        </label>
        <label class="account-field">状态
          <select v-model="status" aria-label="状态" :disabled="loading" @change="searchUsers"><option value="all">全部状态</option><option value="active">正常</option><option value="disabled">已停用</option></select>
        </label>
        <button type="submit" class="account-secondary" :disabled="loading"><PlannerIcon name="refresh" />查询</button>
      </form>
      <div class="admin-results" aria-live="polite"><h2>用户列表 <span>{{ total }}</span></h2><span>{{ loading ? '加载中…' : `第 ${page} / ${pages} 页` }}</span></div>
      <p class="admin-location-note"><PlannerIcon name="location" />位置来自用户使用环境舒适度时的设备上报；后台或锁屏可能暂停更新。</p>
      <p v-if="locationError" class="account-error" role="alert">{{ locationError }}</p>
      <div class="admin-table-wrap" :aria-busy="loading">
        <table class="admin-table">
          <thead><tr><th scope="col">用户</th><th scope="col">角色</th><th scope="col">状态</th><th scope="col">注册日期</th><th scope="col">位置</th><th scope="col">操作</th></tr></thead>
          <tbody>
            <tr v-for="user in users" :key="user.username">
              <td class="admin-user-cell"><strong>{{ user.displayName }}</strong><span>@{{ user.username }}<small v-if="user.username === auth.user?.username">当前账号</small></span></td>
              <td data-label="角色"><span class="admin-role" :class="{ 'is-admin': user.isAdmin }">{{ user.isAdmin ? '管理员' : '普通用户' }}</span></td>
              <td data-label="状态"><span class="admin-status" :class="{ 'is-disabled': !user.active }"><i aria-hidden="true"></i>{{ user.active ? '正常' : '已停用' }}</span></td>
              <td data-label="注册日期" class="admin-date">{{ formatDate(user.createdAt) }}</td>
              <td data-label="位置" class="admin-location-cell">
                <span :class="{ 'location-live': locations[user.username]?.status === 'live' }">{{ locationLabel(locations[user.username]?.status) }}</span>
                <button v-if="locations[user.username]?.position" type="button" class="admin-location-link" :aria-label="`查看 ${user.username} 的位置`" @click="openLocation(user.username)"><PlannerIcon name="map" />查看位置</button>
              </td>
              <td class="admin-edit-cell">
                <router-link v-if="user.username === auth.user?.username" to="/settings" class="account-secondary"><PlannerIcon name="settings" />个人设置</router-link>
                <button v-else type="button" class="account-secondary" :disabled="loading" :aria-label="`编辑用户 ${user.username}`" @click="openEditor(user)"><PlannerIcon name="edit" />编辑</button>
              </td>
            </tr>
            <tr v-if="!users.length"><td colspan="6" class="admin-empty">{{ loading ? '正在读取用户…' : error ? '暂时无法读取用户列表' : '没有匹配的用户' }}</td></tr>
          </tbody>
        </table>
      </div>
      <nav class="admin-pagination" aria-label="用户分页">
        <span>共 {{ total }} 位用户</span>
        <div>
          <button class="account-secondary admin-icon-button" type="button" title="上一页" aria-label="上一页" :disabled="loading || page <= 1" @click="loadUsers(page - 1)"><PlannerIcon name="left" /></button>
          <span>{{ page }} / {{ pages }}</span>
          <button class="account-secondary admin-icon-button" type="button" title="下一页" aria-label="下一页" :disabled="loading || page >= pages" @click="loadUsers(page + 1)"><PlannerIcon name="right" /></button>
        </div>
      </nav>
      <dialog ref="locationDialog" class="admin-dialog admin-location-dialog" aria-labelledby="admin-location-title" @close="selectedLocationUser = ''">
        <header class="admin-dialog-heading"><div><p class="account-eyebrow">@{{ selectedLocationUser }}</p><h2 id="admin-location-title">用户位置</h2></div><button type="button" class="account-secondary admin-icon-button" title="关闭" aria-label="关闭用户位置" @click="locationDialog?.close()"><PlannerIcon name="close" /></button></header>
        <template v-if="selectedLocation?.position">
          <p class="admin-location-state" :class="{ 'location-live': selectedLocation.status === 'live' }"><PlannerIcon name="location" />{{ locationLabel(selectedLocation.status) }}</p>
          <dl class="admin-location-details">
            <div><dt>纬度 / 经度</dt><dd>{{ selectedLocation.position.latitude.toFixed(6) }} / {{ selectedLocation.position.longitude.toFixed(6) }}</dd></div>
            <div><dt>定位精度</dt><dd>约 {{ Math.round(selectedLocation.position.accuracy) }} 米</dd></div>
            <div><dt>设备采集时间</dt><dd>{{ locationTime(selectedLocation.position.capturedAt) }}</dd></div>
            <div><dt>服务器接收时间</dt><dd>{{ locationTime(selectedLocation.position.receivedAt) }}</dd></div>
          </dl>
          <iframe v-if="showMap" :src="mapUrl" title="用户上报位置的 OpenStreetMap 地图" class="admin-location-map" referrerpolicy="no-referrer"></iframe>
          <button v-else type="button" class="account-secondary" @click="showMap = true"><PlannerIcon name="map" />在地图中查看</button>
          <p class="admin-location-note">地图由 OpenStreetMap 提供。{{ selectedLocation.status === 'live' ? '本页约每 15 秒检查一次最新上报。' : '这是最后一次上报的位置，不代表用户当前所在位置。' }}</p>
        </template>
        <p v-else class="account-caption" role="status">{{ locationError || (selectedLocation?.status === 'expired' ? '位置已过期，等待用户重新使用环境舒适度。' : '当前没有可查看的位置，用户可能已经退出环境舒适度。') }}</p>
      </dialog>
      <dialog ref="dialog" class="admin-dialog" aria-labelledby="admin-edit-title" @cancel="cancelDialog" @click="backdropClose">
        <template v-if="editing">
          <header class="admin-dialog-heading"><div><p class="account-eyebrow">@{{ editing.username }}</p><h2 id="admin-edit-title">编辑用户</h2></div><button type="button" class="account-secondary admin-icon-button" title="关闭" aria-label="关闭编辑用户" :disabled="saving" @click="closeEditor"><PlannerIcon name="close" /></button></header>
          <p v-if="editorError" class="account-error" role="alert" tabindex="-1" ref="editorAlert">{{ editorError }}</p>
          <p v-if="editorNotice" class="account-notice" role="status">{{ editorNotice }}</p>
          <form @submit.prevent="saveUser">
            <fieldset :disabled="saving">
              <label class="account-field">昵称<input v-model="form.displayName" maxlength="40" required autofocus /></label>
              <label class="account-field">默认计划<select v-model="form.defaultPeriod" aria-label="默认计划"><option value="day">日计划</option><option value="week">周计划</option><option value="month">月计划</option><option value="year">年计划</option></select></label>
              <div class="admin-checks"><label><input v-model="form.active" type="checkbox" />账号启用</label><label><input v-model="form.isAdmin" type="checkbox" />管理员权限</label></div>
              <p class="admin-security-note">保存后该用户需要重新登录；管理员可管理平台账号。</p>
              <div class="admin-dialog-actions"><button type="button" class="account-secondary" @click="closeEditor">取消</button><button type="submit" class="account-primary"><PlannerIcon name="saved" />{{ saving ? '处理中…' : '保存用户' }}</button></div>
            </fieldset>
          </form>
          <form class="admin-password-form" @submit.prevent="resetPassword">
            <fieldset :disabled="saving">
              <h3>重置密码</h3>
              <label class="account-field">新密码<input v-model="newPassword" type="password" autocomplete="new-password" minlength="10" maxlength="128" required placeholder="至少 10 位" /></label>
              <div class="admin-dialog-actions"><button type="submit" class="account-secondary"><PlannerIcon name="lock" />重置密码</button></div>
            </fieldset>
          </form>
        </template>
      </dialog>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth, authRequest, loadSession } from '@/auth'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'

interface ManagedUser {
  username: string
  displayName: string
  isAdmin: boolean
  active: boolean
  preferences: { defaultPeriod: string }
  revision: number
  createdAt: string
}
interface UserList { users: ManagedUser[]; total: number; page: number; pageSize: number }
interface UserLocation {
  username: string
  status: string
  position: null | { latitude: number; longitude: number; accuracy: number; capturedAt: string; receivedAt: string }
}
const router = useRouter()
const users = ref<ManagedUser[]>([])
const total = ref(0)
const page = ref(1)
const pages = computed(() => Math.max(1, Math.ceil(total.value / 25)))
const query = ref('')
const role = ref('all')
const status = ref('all')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const editing = ref<ManagedUser | null>(null)
const form = ref({ displayName: '', defaultPeriod: 'day', active: true, isAdmin: false })
const newPassword = ref('')
const dialog = ref<HTMLDialogElement>()
const editorAlert = ref<HTMLElement>()
const editorError = ref('')
const editorNotice = ref('')
const locations = ref<Record<string, UserLocation>>({})
const locationError = ref('')
const locationDialog = ref<HTMLDialogElement>()
const selectedLocationUser = ref('')
const showMap = ref(false)
const selectedLocation = computed(() => locations.value[selectedLocationUser.value])
let locationVersion = 0
let locationTimer: ReturnType<typeof setInterval> | undefined
let disposed = false
const mapUrl = computed(() => {
  const position = selectedLocation.value?.position
  if (!position) return ''
  const { latitude: lat, longitude: lon } = position
  const params = new URLSearchParams({
    bbox: [Math.max(-180, lon - .015), Math.max(-85, lat - .01), Math.min(180, lon + .015), Math.min(85, lat + .01)].join(','),
    layer: 'mapnik', marker: `${lat},${lon}`
  })
  return `https://www.openstreetmap.org/export/embed.html?${params}`
})
function locationLabel(status?: string) {
  return ({ live: '最近更新', stale: '最后位置', expired: '位置已过期', waiting: '等待定位', not_shared: '未在使用', disabled: '账号停用' } as Record<string, string>)[status || ''] || '正在读取'
}
function locationTime(value: string) { return new Date(value).toLocaleString('zh-CN', { hour12: false }) }
async function openLocation(username: string) {
  selectedLocationUser.value = username
  showMap.value = false
  await nextTick()
  locationDialog.value?.showModal()
}
async function loadLocations() {
  const names = users.value.map(user => user.username)
  if (!names.length || document.hidden || disposed) return
  const version = ++locationVersion
  try {
    const result = await authRequest<{ locations: UserLocation[] }>(`/api/admin/locations?${new URLSearchParams({ users: names.join(',') })}`)
    if (version !== locationVersion || disposed) return
    locations.value = Object.fromEntries(result.locations.map(item => [item.username, item]))
    locationError.value = ''
  } catch (failure) {
    if (version !== locationVersion || disposed) return
    locations.value = {}
    locationError.value = failure instanceof Error ? failure.message : '位置读取失败。'
    await checkAccess()
  }
}
function locationVisibilityChanged() {
  if (document.hidden) { ++locationVersion; locations.value = {} }
  else void loadLocations()
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
async function checkAccess() {
  await loadSession()
  if (auth.localMode || !auth.user?.isAdmin) {
    dialog.value?.close()
    locationDialog.value?.close()
    await router.replace(auth.user ? '/tools' : '/login')
    return false
  }
  return true
}
async function loadUsers(targetPage = page.value) {
  if (loading.value) return
  loading.value = true
  ++locationVersion
  locations.value = {}
  error.value = ''
  try {
    const params = new URLSearchParams({ q: query.value.trim(), role: role.value, status: status.value, page: String(targetPage) })
    const result = await authRequest<UserList>(`/api/admin/users?${params}`)
    users.value = result.users
    total.value = result.total
    page.value = result.page
    void loadLocations()
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : '读取用户失败。'
    await checkAccess()
  } finally { loading.value = false }
}
function searchUsers() { void loadUsers(1) }
async function openEditor(user: ManagedUser) {
  editing.value = { ...user }
  form.value = { displayName: user.displayName, defaultPeriod: user.preferences.defaultPeriod, active: user.active, isAdmin: user.isAdmin }
  newPassword.value = ''
  editorError.value = ''
  editorNotice.value = ''
  await nextTick()
  dialog.value?.showModal()
}
function closeEditor() {
  if (saving.value) return
  dialog.value?.close()
  editing.value = null
  newPassword.value = ''
}
function cancelDialog(event: Event) {
  event.preventDefault()
  closeEditor()
}
function backdropClose(event: MouseEvent) {
  if (event.target !== dialog.value) return
  const bounds = dialog.value.getBoundingClientRect()
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeEditor()
}
async function saveUser() {
  if (!editing.value || saving.value) return
  const target = editing.value
  saving.value = true
  editorError.value = ''
  editorNotice.value = ''
  try {
    await authRequest(`/api/admin/users/${target.username}`, 'PATCH', { ...form.value, revision: target.revision })
    notice.value = `已更新 @${target.username}，该用户需要重新登录。`
    saving.value = false
    closeEditor()
    await loadUsers()
  } catch (failure) {
    editorError.value = failure instanceof Error ? failure.message : '保存失败。'
    if (await checkAccess()) { await nextTick(); editorAlert.value?.focus() }
  } finally { saving.value = false }
}
async function resetPassword() {
  if (!editing.value || saving.value) return
  saving.value = true
  editorError.value = ''
  editorNotice.value = ''
  try {
    const result = await authRequest<{ user: ManagedUser; message: string }>(`/api/admin/users/${editing.value.username}/password`, 'POST', {
      revision: editing.value.revision, newPassword: newPassword.value
    })
    editing.value = result.user
    newPassword.value = ''
    editorNotice.value = result.message
    await loadUsers()
  } catch (failure) {
    editorError.value = failure instanceof Error ? failure.message : '重置密码失败。'
    if (await checkAccess()) { await nextTick(); editorAlert.value?.focus() }
  } finally { saving.value = false }
}
onMounted(() => {
  void loadUsers()
  locationTimer = setInterval(() => { if (!loading.value) void loadLocations() }, 15000)
  document.addEventListener('visibilitychange', locationVisibilityChanged)
})
onUnmounted(() => {
  disposed = true
  ++locationVersion
  clearInterval(locationTimer)
  document.removeEventListener('visibilitychange', locationVisibilityChanged)
})
</script>

<style src="@/components/account/account.css"></style>
<style scoped>
.admin-eyebrow { color: #287582; font-weight: 600; }
.admin-toolbar { display: grid; grid-template-columns: minmax(160px, 1fr) 150px 150px auto; align-items: end; gap: 16px; padding: 20px 0 26px; border-bottom: 1px solid #dbe3df; }
.admin-results { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin: 24px 0 14px; }
.admin-results h2 span { margin-left: 8px; color: #64786b; font-size: 14px; font-weight: 400; }
.admin-results > span, .admin-pagination { font-size: 13px; color: #596f61; }
.admin-table-wrap { min-width: 0; }
.admin-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px; }
.admin-table th { text-align: left; color: #586d60; font-weight: 500; font-size: 12px; background: #eaf0ec; padding: 12px 16px; }
.admin-table th:first-child { width: 23%; }
.admin-table th:nth-child(5) { width: 130px; }
.admin-table th:last-child { width: 140px; }
.admin-table td { padding: 18px 16px; border-bottom: 1px solid #dbe3df; overflow-wrap: anywhere; vertical-align: middle; }
.admin-user-cell strong { display: block; font-size: 15px; font-weight: 600; }
.admin-user-cell > span { font-size: 12px; color: #63776a; display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.admin-user-cell small { font-size: 11px; color: #277381; }
.admin-role { font-size: 12px; }
.admin-role.is-admin { color: #277381; }
.admin-status { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; }
.admin-status i { width: 6px; height: 6px; border-radius: 50%; background: #50836a; flex-shrink: 0; }
.admin-status.is-disabled { color: #a2473d; }
.admin-status.is-disabled i { background: #b9675b; }
.admin-date { font-variant-numeric: tabular-nums; color: #586d60; font-size: 12px; }
.admin-edit-cell .account-secondary { padding: 8px 12px; font-size: 13px; white-space: nowrap; }
.admin-empty { text-align: center; color: #63776a; height: 160px; }
.admin-pagination { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 22px 0; }
.admin-pagination > div { display: flex; align-items: center; gap: 16px; }
.admin-icon-button { width: 44px; height: 44px; padding: 0; flex-shrink: 0; }
.admin-dialog { padding: 24px; width: 480px; max-width: calc(100% - 32px); max-height: calc(100dvh - 32px); overflow: auto; border: 1px solid #cbd9d1; border-radius: 8px; background: #fff; color: #293b33; }
.admin-dialog::backdrop { background: #172d2466; }
.admin-dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
.admin-dialog fieldset { gap: 18px; }
.admin-checks { display: flex; gap: 24px; flex-wrap: wrap; }
.admin-checks label { display: inline-flex; gap: 10px; align-items: center; min-height: 44px; font-size: 14px; cursor: pointer; }
.admin-checks input { width: 18px; height: 18px; accent-color: #50836a; }
.admin-security-note { font-size: 12px; color: #64786b; margin: 0; }
.admin-dialog-actions { display: flex; justify-content: flex-end; gap: 12px; }
.admin-password-form { padding-top: 22px; margin-top: 24px; border-top: 1px solid #dbe3df; }
.admin-password-form h3 { font-size: 15px; margin: 0; }
.admin-screen > .account-content { max-width: 1100px; }
.admin-location-note { color: #62756a; font-size: 12px; margin: 12px 0 20px; }
.admin-location-note > svg { margin-right: 6px; }
.admin-location-cell > span { font-size: 12px; color: #687c70; }
.admin-location-link { border: 0; padding: 6px 0; background: none; color: #2b7380; font-size: 12px !important; min-height: 44px; display: flex; align-items: center; gap: 6px; text-decoration: underline; text-underline-offset: 4px; }
.location-live { color: #2a7b58 !important; }
.admin-location-dialog { width: 600px; }
.admin-location-state { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.admin-location-details { display: grid; gap: 12px; font-size: 13px; padding: 18px 0; border-block: 1px solid #e1e8e3; }
.admin-location-details > div { display: flex; gap: 16px; justify-content: space-between; flex-wrap: wrap; }
.admin-location-details dt { color: #65786c; }
.admin-location-details dd { margin: 0; overflow-wrap: anywhere; }
.admin-location-map { display: block; width: 100%; height: 280px; border: 1px solid #d4dfd8; margin-top: 20px; border-radius: 6px; }
@media (max-width: 700px) {
  .admin-toolbar { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
  .admin-search { grid-column: 1 / -1; }
  .admin-toolbar > button { grid-column: 1 / -1; }
  .admin-table thead { display: none; }
  .admin-table, .admin-table tbody { display: block; }
  .admin-table tr { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px 16px; padding: 18px 0; border-bottom: 1px solid #dbe3df; }
  .admin-table td { display: block; border: 0; padding: 4px 0; min-width: 0; }
  .admin-user-cell { grid-column: 1 / -1; }
  .admin-location-cell { grid-column: 1 / -1; }
  .admin-location-link { display: inline-flex; margin-left: 16px; }
  .admin-table td[data-label]::before { content: attr(data-label); font-size: 12px; color: #63776a; margin-right: 12px; }
  .admin-edit-cell { display: flex !important; justify-content: flex-end; align-items: center; }
  .admin-table .admin-empty { grid-column: 1 / -1; display: grid; place-items: center; }
  .admin-dialog { padding: 20px; }
}
</style>
