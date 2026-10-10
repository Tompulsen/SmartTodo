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
      <div class="admin-table-wrap" :aria-busy="loading">
        <table class="admin-table">
          <thead><tr><th scope="col">用户</th><th scope="col">角色</th><th scope="col">状态</th><th scope="col">注册日期</th><th scope="col">操作</th></tr></thead>
          <tbody>
            <tr v-for="user in users" :key="user.username">
              <td class="admin-user-cell"><strong>{{ user.displayName }}</strong><span>@{{ user.username }}<small v-if="user.username === auth.user?.username">当前账号</small></span></td>
              <td data-label="角色"><span class="admin-role" :class="{ 'is-admin': user.isAdmin }">{{ user.isAdmin ? '管理员' : '普通用户' }}</span></td>
              <td data-label="状态"><span class="admin-status" :class="{ 'is-disabled': !user.active }"><i aria-hidden="true"></i>{{ user.active ? '正常' : '已停用' }}</span></td>
              <td data-label="注册日期" class="admin-date">{{ formatDate(user.createdAt) }}</td>
              <td class="admin-edit-cell">
                <router-link v-if="user.username === auth.user?.username" to="/settings" class="account-secondary"><PlannerIcon name="settings" />个人设置</router-link>
                <button v-else type="button" class="account-secondary" :disabled="loading" :aria-label="`编辑用户 ${user.username}`" @click="openEditor(user)"><PlannerIcon name="edit" />编辑</button>
              </td>
            </tr>
            <tr v-if="!users.length"><td colspan="5" class="admin-empty">{{ loading ? '正在读取用户…' : error ? '暂时无法读取用户列表' : '没有匹配的用户' }}</td></tr>
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
import { computed, nextTick, onMounted, ref } from 'vue'
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

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}
async function checkAccess() {
  await loadSession()
  if (auth.localMode || !auth.user?.isAdmin) {
    dialog.value?.close()
    await router.replace(auth.user ? '/tools' : '/login')
    return false
  }
  return true
}
async function loadUsers(targetPage = page.value) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ q: query.value.trim(), role: role.value, status: status.value, page: String(targetPage) })
    const result = await authRequest<UserList>(`/api/admin/users?${params}`)
    users.value = result.users
    total.value = result.total
    page.value = result.page
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
onMounted(() => { void loadUsers() })
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
.admin-table th:first-child { width: 31%; }
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
@media (max-width: 700px) {
  .admin-toolbar { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
  .admin-search { grid-column: 1 / -1; }
  .admin-toolbar > button { grid-column: 1 / -1; }
  .admin-table thead { display: none; }
  .admin-table, .admin-table tbody { display: block; }
  .admin-table tr { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 6px 16px; padding: 18px 0; border-bottom: 1px solid #dbe3df; }
  .admin-table td { display: block; border: 0; padding: 4px 0; min-width: 0; }
  .admin-user-cell { grid-column: 1 / -1; }
  .admin-table td[data-label]::before { content: attr(data-label); font-size: 12px; color: #63776a; margin-right: 12px; }
  .admin-edit-cell { display: flex !important; justify-content: flex-end; align-items: center; }
  .admin-table .admin-empty { grid-column: 1 / -1; display: grid; place-items: center; }
  .admin-dialog { padding: 20px; }
}
</style>
