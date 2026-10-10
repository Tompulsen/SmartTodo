import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sourceUrl } from './load-source.mjs'

const http = await import(sourceUrl('../src/http.ts'))

test('unsafe API requests carry current CSRF token and preserve multipart headers', async (t) => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async (path, init) => {
    calls.push([path, init])
    return new Response('{}')
  })
  http.setCsrfToken('first-session')
  const file = new FormData()
  file.set('myFile', new Blob(['sample']), 'sample.txt')
  await http.apiFetch('/api/file/upload', { method: 'POST', body: file })
  assert.equal(calls[0][1].headers.get('X-CSRF-Token'), 'first-session')
  assert.equal(calls[0][1].headers.has('Content-Type'), false)
  assert.equal(calls[0][1].body, file)
  http.setCsrfToken('second-session')
  await http.apiFetch('/api/account/profile', { method: 'PATCH', headers: { 'Content-Type': 'application/json' } })
  assert.equal(calls[1][1].headers.get('X-CSRF-Token'), 'second-session')
  assert.equal(calls[1][1].credentials, 'same-origin')
  await http.apiFetch('/api/planner/day/2026-10-10')
  assert.equal(calls[2][1].headers.has('X-CSRF-Token'), false)
})

test('expired data sessions require login while invalid login credentials stay on form', async (t) => {
  const previous = globalThis.window
  const target = new EventTarget()
  globalThis.window = target
  t.after(() => { globalThis.window = previous })
  let redirected = 0
  target.addEventListener('auth-required', () => redirected++)
  t.mock.method(globalThis, 'fetch', async () => new Response('{}', { status: 401 }))
  await http.apiFetch('/api/login', { method: 'POST' })
  await http.apiFetch('/api/auth/register', { method: 'POST' })
  assert.equal(redirected, 0)
  await http.apiFetch('/api/focus/state')
  assert.equal(redirected, 1)
})

test('network errors propagate to callers instead of becoming false successes', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('offline') })
  await assert.rejects(http.apiFetch('/api/planner/day/2026-10-10'), /offline/)
})
