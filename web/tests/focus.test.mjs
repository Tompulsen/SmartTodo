import assert from 'node:assert/strict'
import { test } from 'node:test'
import { sourceUrl } from './load-source.mjs'

const { focusElapsed, focusSeconds, clockLabel } = await import(sourceUrl('../src/components/focus/focus.ts'))
const base = { status: 'running', resumedAt: 1000000, elapsedMs: 0, duration: 1500 }

test('focus countdown uses elapsed wall time, not the number of timer ticks', () => {
  assert.equal(focusSeconds(base, 1000000), 1500)
  assert.equal(focusSeconds(base, 1000500), 1500)
  assert.equal(focusSeconds(base, 1075000), 1425)
  assert.equal(focusSeconds(base, 2600000), 0)
  assert.equal(focusElapsed(base, 2600000), 1500000)
})
test('paused timers do not count time until resumed', () => {
  const paused = { ...base, status: 'paused', resumedAt: null, elapsedMs: 120000 }
  assert.equal(focusElapsed(paused, 9000000), 120000)
  assert.equal(focusSeconds(paused, 9000000), 1380)
  assert.equal(focusSeconds({ ...paused, status: 'running', resumedAt: 9000000 }, 9030000), 1350)
})
test('stopwatch, clock rollback and restored completed sessions are bounded', () => {
  assert.equal(focusSeconds({ ...base, duration: 0 }, 1065500), 65)
  assert.equal(focusElapsed(base, 900000), 0)
  assert.equal(focusSeconds({ ...base, duration: 0 }, 100000000), 86400)
  assert.equal(focusElapsed({ ...base, status: 'completed', elapsedMs: 1500000, resumedAt: null }, 9000000), 1500000)
})
test('clock labels keep stable units across minutes and hours', () => {
  assert.equal(clockLabel(0), '00:00')
  assert.equal(clockLabel(1500), '25:00')
  assert.equal(clockLabel(3661), '01:01:01')
  assert.equal(clockLabel(-2), '00:00')
})
