<template>
  <main class="account-screen login-screen">
    <header class="account-topbar"><span class="account-brand">SmartTodo<span>.</span></span><span class="account-topnote">把时间留给重要的事</span></header>
    <section class="login-panel" aria-labelledby="login-title">
      <div class="account-mark"><PlannerIcon :name="register ? 'user' : 'lock'" /></div>
      <h1 id="login-title">{{ register ? '创建你的账号' : '欢迎回来' }}</h1>
      <p class="account-caption">{{ register ? '从今天开始，安排自己的每一天。' : '登录 SmartTodo，继续你的计划。' }}</p>
      <nav class="account-tabs" aria-label="账号操作">
        <router-link :to="{ path: '/login', query: route.query }" :aria-current="!register ? 'page' : undefined">登录</router-link>
        <router-link v-if="auth.registrationEnabled" :to="{ path: '/register', query: route.query }" :aria-current="register ? 'page' : undefined">注册</router-link>
      </nav>
      <p v-if="route.query.changed && !register" class="account-notice" role="status">密码已修改，请使用新密码登录。</p>
      <p v-if="error || auth.error" class="account-error" role="alert">{{ error || auth.error }}</p>
      <p v-if="register && !auth.registrationEnabled" class="account-notice">此站点暂未开放注册。</p>
      <form v-else @submit.prevent="submit">
        <fieldset :disabled="pending">
          <div class="account-field"><label for="account-username">账号</label>
            <input id="account-username" v-model="username" name="username" autocomplete="username" required :minlength="register ? 4 : undefined" maxlength="15"
              :pattern="register ? '[a-zA-Z][a-zA-Z0-9_]{3,14}' : undefined" autocapitalize="none" :spellcheck="false" autofocus
              placeholder="请输入账号" :aria-describedby="register ? 'username-hint' : undefined" />
            <small v-if="register" id="username-hint">4–15 位字母、数字或下划线，以字母开头。</small>
          </div>
          <label v-if="register" class="account-field">昵称
            <input v-model="displayName" name="nickname" autocomplete="nickname" maxlength="40" placeholder="怎么称呼你（选填）" />
          </label>
          <div class="account-field">
            <label for="account-password">密码</label>
            <div class="password-input">
              <input id="account-password" v-model="password" name="password" :type="showPassword ? 'text' : 'password'"
                :autocomplete="register ? 'new-password' : 'current-password'" required :minlength="register ? 10 : undefined"
                maxlength="128" placeholder="请输入密码" :aria-describedby="register ? 'password-hint' : undefined" />
              <button type="button" class="account-icon" :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :title="showPassword ? '隐藏密码' : '显示密码'" :aria-pressed="showPassword" @click="showPassword = !showPassword"><PlannerIcon :name="showPassword ? 'eye-slash' : 'eye'" /></button>
            </div>
            <small v-if="register" id="password-hint">至少 10 位。</small>
          </div>
          <label v-if="register" class="account-field">确认密码
            <input v-model="confirmation" name="password-confirmation" :type="showPassword ? 'text' : 'password'" autocomplete="new-password"
              required minlength="10" maxlength="128" placeholder="再输入一次密码" />
          </label>
          <button class="account-primary login-submit" type="submit"><PlannerIcon :name="pending ? 'clock' : register ? 'plus' : 'right'" />{{ pending ? '正在提交…' : register ? '创建账号' : '登录' }}</button>
        </fieldset>
      </form>
      <p class="login-footer"><PlannerIcon name="shield" />你的计划，属于你的账号</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import { auth, safeReturnPath, signIn } from '@/auth'

const route = useRoute()
const router = useRouter()
const register = computed(() => route.path === '/register')
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmation = ref('')
const showPassword = ref(false)
const pending = ref(false)
const error = ref('')
async function submit() {
  if (pending.value) return
  error.value = ''
  if (register.value && password.value !== confirmation.value) {
    error.value = '两次输入的密码不一致。'
    return
  }
  pending.value = true
  try {
    await signIn(register.value, { username: username.value, password: password.value,
      ...(register.value && displayName.value.trim() ? { displayName: displayName.value.trim() } : {}) })
    password.value = confirmation.value = ''
    await router.replace(safeReturnPath(route.query.redirect))
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '连接失败，请稍后再试。'
  } finally { pending.value = false }
}
</script>

<style src="@/components/account/account.css"></style>
