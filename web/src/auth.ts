import { reactive } from 'vue'
import { apiFetch, setCsrfToken } from './http'
import type { PlanPeriod } from './components/planner/planner'

export interface Account {
  username: string
  displayName: string
  isAdmin: boolean
  preferences: { defaultPeriod: PlanPeriod }
}
interface SessionReply {
  user: Account | null
  csrfToken: string
  localMode: boolean
  registrationEnabled?: boolean
}
export const auth = reactive({
  user: null as Account | null, localMode: false, registrationEnabled: true,
  ready: false, error: ''
})

export async function authRequest<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method, signal: AbortSignal.timeout(15000),
    ...(data === undefined ? {} : { body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' } })
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(result.error || '请求失败，请稍后重试。')
  return result
}

function acceptSession(result: SessionReply) {
  auth.user = result.user
  auth.localMode = result.localMode
  if (result.registrationEnabled !== undefined) auth.registrationEnabled = result.registrationEnabled
  setCsrfToken(result.csrfToken)
  auth.ready = true
  auth.error = ''
}

export async function loadSession() {
  try {
    acceptSession(await authRequest<SessionReply>('/api/auth/session'))
    return true
  } catch {
    auth.error = '暂时无法连接服务，请稍后重试。'
    return false
  }
}

export async function signIn(register: boolean, data: { username: string; password: string; displayName?: string }) {
  if (!await loadSession()) throw new Error(auth.error)
  acceptSession(await authRequest<SessionReply>(register ? '/api/auth/register' : '/api/login', 'POST', data))
}

export async function signOut() {
  acceptSession(await authRequest<SessionReply>('/api/logout', 'POST'))
}

export function safeReturnPath(value: unknown) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') &&
    !value.includes('\\') && !/[\r\n]/.test(value) && !/^\/(login|register)([/?#]|$)/.test(value) ? value : '/index'
}
