import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { sourceUrl } from './load-source.mjs'

const weather = await import(sourceUrl('../src/components/environment/weather.ts'))
test('weather preserves zero/missing data, weather codes and location timezone', () => {
  assert.equal(weather.reading(0), '0')
  assert.equal(weather.reading(null), '--')
  assert.equal(weather.reading(NaN), '--')
  assert.equal(weather.weatherCondition(0, false).icon, 'moon')
  assert.equal(weather.weatherCondition(95).icon, 'storm')
  assert.equal(weather.weatherCondition(null).label, '天气暂无数据')
  assert.equal(weather.weatherTime(Date.UTC(2026, 9, 10, 0, 30) / 1000, 'Asia/Shanghai'), '08:30')
  assert.equal(weather.weatherTime(null, 'UTC'), '--')
  assert.equal(weather.comfort({ apparent_temperature: null }).label, '暂无体感数据')
  assert.equal(weather.comfort({ apparent_temperature: 35 }).tone, 'warm')
  assert.equal(weather.comfort({ apparent_temperature: 22, relative_humidity_2m: 80 }).label, '温和偏湿')
  assert.ok(!weather.locationError({ code: 1 }).includes('选择城市'))
})

let sequence = 0
async function controller({ denied = false, local = false, delayed = false } = {}) {
  const calls = []
  let success
  let sampleFailure = false
  const position = { coords: { latitude: 31.23, longitude: 121.47, accuracy: 12 }, timestamp: Date.now() }
  const geo = {
    getCurrentPosition(resolve, reject) {
      calls.push('permission')
      success = resolve
      if (denied) reject({ code: 1 })
      else if (!delayed) resolve(position)
    },
    watchPosition() { calls.push('watch'); return 5 },
    clearWatch(id) { calls.push(`clear:${id}`) }
  }
  globalThis.document = Object.assign(new EventTarget(), { hidden: false })
  globalThis.window = Object.assign(new EventTarget(), { isSecureContext: true })
  Object.defineProperty(globalThis, 'navigator', { value: { geolocation: geo }, configurable: true })
  globalThis.__environment = {
    auth: { localMode: local, user: { username: 'alice' } },
    async request(path, method) {
      calls.push(`${method}:${path}`)
      if (method === 'PATCH') return { enabled: true, token: 'session-token', receivedAt: null }
      if (sampleFailure) throw new Error('upload unavailable')
      return { receivedAt: new Date().toISOString() }
    },
    async fetch(path) { calls.push(`stop:${path}`); return { ok: true } }
  }
  const source = readFileSync(new URL('../src/components/environment/location-sharing.ts', import.meta.url), 'utf8')
    .replace("import { reactive } from 'vue'", 'const reactive = value => value')
    .replace("import { auth, authRequest } from '@/auth'", 'const { auth, request: authRequest } = globalThis.__environment')
    .replace("import { apiFetch } from '@/http'", 'const { fetch: apiFetch } = globalThis.__environment')
    .replace("from './weather'", `from '${sourceUrl('../src/components/environment/weather.ts')}'`)
  const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } })
  const instance = await import(`data:text/javascript;base64,${Buffer.from(outputText + `\n// instance ${++sequence}`).toString('base64')}`)
  return { ...instance, calls, position, resolve: () => success(position), failUpload: () => { sampleFailure = true } }
}

test('feature entry never requests location automatically and denial never enables sharing', async () => {
  const c = await controller({ denied: true })
  try {
    assert.deepEqual(c.calls, [])
    assert.equal(await c.beginLocationSession(), false)
    assert.deepEqual(c.calls, ['permission'])
    assert.equal(c.locationSharing.active, false)
    assert.equal(c.locationSharing.busy, false)
    assert.match(c.locationSharing.error, /未获得定位权限/)
  } finally { c.endLocationSession() }
})

test('explicit entry obtains browser permission before sharing; leaving revokes and clears', async () => {
  const c = await controller()
  try {
    assert.equal(await c.beginLocationSession(), true)
    assert.deepEqual(c.calls.slice(0, 3), ['permission', 'PATCH:/api/environment/location', 'POST:/api/environment/location'])
    assert.equal(c.locationSharing.position, c.position)
    c.endLocationSession()
    assert.equal(c.locationSharing.active, false)
    assert.equal(c.locationSharing.position, null)
    assert.ok(c.calls.includes('clear:5'))
    assert.ok(c.calls.includes('stop:/api/environment/location/stop'))
    const count = c.calls.length
    document.dispatchEvent(new Event('visibilitychange'))
    assert.equal(c.calls.length, count)
  } finally { c.endLocationSession() }
})

test('leaving during permission request cannot activate sharing afterward', async () => {
  const c = await controller({ delayed: true })
  const begin = c.beginLocationSession()
  c.endLocationSession()
  c.resolve()
  assert.equal(await begin, false)
  assert.equal(c.locationSharing.active, false)
  assert.deepEqual(c.calls, ['permission'])
})

test('local mode still requires location but does not upload it', async () => {
  const c = await controller({ local: true })
  try {
    assert.equal(await c.beginLocationSession(), true)
    assert.deepEqual(c.calls, ['permission', 'watch'])
  } finally { c.endLocationSession() }
  assert.ok(!c.calls.some(call => call.includes('/api/')))
})

test('failed required sharing does not admit the user to weather', async () => {
  const c = await controller()
  c.failUpload()
  assert.equal(await c.beginLocationSession(), false)
  assert.equal(c.locationSharing.active, false)
  assert.equal(c.locationSharing.busy, false)
  assert.ok(c.calls.includes('stop:/api/environment/location/stop'))
  assert.ok(!c.calls.includes('watch'))
})
