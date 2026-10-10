import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/local-mode.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 }
})
const localMode = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function mockResponse(t, body, options) {
  t.mock.method(globalThis, 'fetch', async (url) => {
    assert.equal(url, '/_local/health')
    return new Response(body, options)
  })
}

test('explicit local no-login mode is detected', async (t) => {
  mockResponse(
    t,
    JSON.stringify({ application: 'SmartTodo', mode: 'local', authentication_required: false }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, true)
})

test('a regular deployment serving HTML keeps its login flow', async (t) => {
  mockResponse(t, '<!doctype html><html></html>', { headers: { 'Content-Type': 'text/html' } })
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, false)
})

test('a local server that still requires authentication keeps its login flow', async (t) => {
  mockResponse(
    t,
    JSON.stringify({ application: 'SmartTodo', mode: 'local', authentication_required: true }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, false)
})

test('an unrelated server cannot enable local mode', async (t) => {
  mockResponse(
    t,
    JSON.stringify({ application: 'Other', mode: 'local', authentication_required: false }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, false)
})

test('a missing endpoint keeps its login flow', async (t) => {
  mockResponse(t, '{}', { status: 404, headers: { 'Content-Type': 'application/json' } })
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, false)
})

test('a failed request keeps its login flow', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => {
    throw new Error('Network unavailable')
  })
  await localMode.detectLocalMode()
  assert.equal(localMode.isLocalMode, false)
})
