<template>
  <main class="account-screen">
    <div class="account-content">
      <header class="account-topbar">
        <router-link to="/index" class="account-brand">SmartTodo<span>.</span></router-link>
        <router-link to="/tools" class="account-back"><PlannerIcon name="back" />工具箱</router-link>
      </header>
      <div class="account-heading"><div><p class="account-eyebrow">个人空间</p><h1>设置</h1></div><span class="account-mode">{{ auth.localMode ? '本机使用' : '账号已连接' }}</span></div>
      <p v-if="error" class="account-error" role="alert">{{ error }}</p>
      <p v-if="notice" class="account-notice" role="status">{{ notice }}</p>
      <section class="account-section" aria-labelledby="profile-title">
        <div class="account-section-label"><PlannerIcon name="user" /><h2 id="profile-title">个人资料</h2></div>
        <form @submit.prevent="saveProfile">
          <fieldset :disabled="!!pending || auth.localMode">
            <div class="account-identity"><span class="account-avatar">{{ (auth.user?.displayName || 'S').slice(0, 1).toUpperCase() }}</span>
              <div><strong>{{ auth.user?.displayName }}</strong><span>{{ auth.user?.username }} · {{ auth.localMode ? '本地用户' : auth.user?.isAdmin ? '管理员' : '个人账号' }}</span></div>
            </div>
            <label class="account-field">昵称<input v-model="displayName" name="nickname" autocomplete="nickname" required maxlength="40" /></label>
            <div class="account-field"><label for="default-period">默认计划</label>
              <select id="default-period" v-model="defaultPeriod" name="default-period"><option value="day">日计划</option><option value="week">周计划</option><option value="month">月计划</option><option value="year">年计划</option></select>
            </div>
            <div class="account-actions"><button type="submit" class="account-primary"><PlannerIcon name="check" />{{ pending === 'profile' ? '保存中…' : '保存设置' }}</button></div>
          </fieldset>
        </form>
      </section>
      <section class="account-section" aria-labelledby="security-title">
        <div class="account-section-label"><PlannerIcon name="lock" /><h2 id="security-title">账号安全</h2></div>
        <p v-if="auth.localMode" class="account-caption">当前使用本机免登录模式。账号注册与密码设置在登录模式下使用。</p>
        <form v-else @submit.prevent="changePassword">
          <fieldset :disabled="!!pending">
            <label class="account-field">当前密码<input v-model="currentPassword" type="password" autocomplete="current-password" required maxlength="128" /></label>
            <div class="account-field"><label for="new-password">新密码</label><input id="new-password" v-model="newPassword" type="password" autocomplete="new-password" required minlength="10" maxlength="128" aria-describedby="new-password-hint" />
              <small id="new-password-hint">至少 10 位。修改后需要在所有设备上重新登录。</small>
            </div>
            <label class="account-field">确认新密码<input v-model="confirmPassword" type="password" autocomplete="new-password" required minlength="10" maxlength="128" /></label>
            <div class="account-actions"><button type="submit" class="account-secondary"><PlannerIcon name="lock" />{{ pending === 'password' ? '修改中…' : '修改密码' }}</button></div>
          </fieldset>
        </form>
      </section>
      <section class="account-section" aria-labelledby="data-title">
        <div class="account-section-label"><PlannerIcon name="saved" /><h2 id="data-title">数据与设备</h2></div>
        <div class="account-data">
          <p>计划与专注记录 <strong>{{ auth.localMode ? '保存在本机' : '保存在当前账号' }}</strong></p>
          <p>上传的专注音频 <strong>保存在当前浏览器</strong></p>
          <button v-if="!auth.localMode" class="account-secondary account-logout" :disabled="!!pending" @click="logout"><PlannerIcon name="logout" />{{ pending === 'logout' ? '退出中…' : '退出登录' }}</button>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import { auth, authRequest, loadSession, signOut, type Account } from '@/auth'
import type { PlanPeriod } from '@/components/planner/planner'

const router = useRouter()
const displayName = ref(auth.user?.displayName || '')
const defaultPeriod = ref<PlanPeriod>(auth.user?.preferences.defaultPeriod || 'day')
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const pending = ref('')
const error = ref('')
const notice = ref('')

async function perform(action: string, work: () => Promise<void>) {
  if (pending.value) return
  error.value = notice.value = ''
  pending.value = action
  try { await work() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '操作失败，请稍后重试。' }
  finally { pending.value = '' }
}
function saveProfile() {
  return perform('profile', async () => {
    const result = await authRequest<{ user: Account }>('/api/account/profile', 'PATCH', { displayName: displayName.value, defaultPeriod: defaultPeriod.value })
    auth.user = result.user
    displayName.value = result.user.displayName
    notice.value = '设置已保存。'
  })
}
function changePassword() {
  return perform('password', async () => {
    if (newPassword.value !== confirmPassword.value) throw new Error('两次输入的新密码不一致。')
    await authRequest('/api/account/password', 'POST', { currentPassword: currentPassword.value, newPassword: newPassword.value })
    currentPassword.value = newPassword.value = confirmPassword.value = ''
    auth.user = null
    await loadSession()
    await router.replace('/login?changed=1')
  })
}
function logout() {
  return perform('logout', async () => {
    await signOut()
    await router.replace('/login')
  })
}
</script>

<style src="@/components/account/account.css"></style>
