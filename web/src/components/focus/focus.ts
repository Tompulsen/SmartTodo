import type { PlanPeriod } from '../planner/planner'
import { apiFetch } from '../../http'

export type FocusMode = 'pomodoro' | 'countdown' | 'stopwatch' | 'break'
export interface FocusLink { period: PlanPeriod; day: string; taskId: string; title: string; section: string }
export interface FocusSession {
  id: string
  mode: FocusMode
  duration: number
  title: string
  link: FocusLink | null
  status: 'running' | 'paused' | 'completed' | 'cancelled'
  elapsedMs: number
  startedAt: number
  resumedAt: number | null
  finishedAt: number | null
}
export interface FocusState { revision: number; session: FocusSession | null; serverNow: number }
export interface FocusRecord {
  id: string; mode: FocusMode; title: string; link: FocusLink | null
  startedAt: number; finishedAt: number; elapsedMs: number; duration: number
}
export interface FocusReport { records: FocusRecord[]; totalMs: number; count: number }

export function focusElapsed(session: FocusSession, now: number): number {
  const extra = session.status === 'running' && session.resumedAt !== null ? Math.max(0, now - session.resumedAt) : 0
  return Math.min((session.duration || 86400) * 1000, session.elapsedMs + extra)
}
export function focusSeconds(session: FocusSession, now: number): number {
  const elapsed = focusElapsed(session, now)
  return session.duration ? Math.max(0, Math.ceil((session.duration * 1000 - elapsed) / 1000)) : Math.floor(elapsed / 1000)
}
export function clockLabel(seconds: number): string {
  const value = Math.max(0, Math.floor(seconds))
  const h = Math.floor(value / 3600)
  const m = Math.floor(value % 3600 / 60)
  const s = value % 60
  return `${h ? `${String(h).padStart(2, '0')}:` : ''}${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
export const modeLabel = (mode: FocusMode) => ({ pomodoro: '\u756a\u8304\u949f', countdown: '\u5012\u8ba1\u65f6', stopwatch: '\u6b63\u8ba1\u65f6', break: '\u4f11\u606f' })[mode]
export class FocusRequestError extends Error { constructor(public status: number) { super(`Focus request failed: ${status}`) } }
export async function focusRequest<T>(path: string, data?: unknown): Promise<T> {
  const response = await apiFetch(`/api/focus${path}`, {
    ...(data ? { method: 'POST', body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' } } : {}),
    signal: AbortSignal.timeout(12000)
  })
  if (!response.ok) throw new FocusRequestError(response.status)
  return response.json()
}
