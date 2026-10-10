import assert from 'node:assert/strict'
import { readFileSync, statSync } from 'node:fs'
import { test } from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/components/focus/audio.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } })
const audio = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

test('audio preferences default to looping, clamp volume and reject corrupt values', () => {
  const defaults = { selectedId: '', volume: .5, muted: false, loop: true }
  for (const value of [null, '', 'null', 'bad JSON', '1']) assert.deepEqual(audio.parseAudioPreferences(value), defaults)
  assert.deepEqual(audio.parseAudioPreferences('{"volume":4,"muted":true,"selectedId":"local:a","loop":false}'),
    { volume: 1, muted: true, selectedId: 'local:a', loop: false })
  assert.equal(audio.parseAudioPreferences('{"volume":-1}').volume, 0)
  assert.equal(audio.parseAudioPreferences('{"volume":"loud","selectedId":5,"muted":"false"}').volume, .5)
})
test('audio uploads validate empty files, size limits, extensions and MIME types', () => {
  assert.ok(audio.audioFileError({ name: 'empty.mp3', type: 'audio/mpeg', size: 0 }))
  assert.ok(audio.audioFileError({ name: 'big.wav', type: 'audio/wav', size: audio.MAX_AUDIO_SIZE + 1 }))
  assert.ok(audio.audioFileError({ name: 'not-audio.html', type: 'text/html', size: 100 }))
  for (const extension of ['mp3', 'WAV', 'm4a', 'aac', 'ogg', 'opus', 'flac', 'weba', 'webm']) {
    assert.equal(audio.audioFileError({ name: `track.${extension}`, size: 100, type: '' }), '')
  }
  assert.equal(audio.audioFileError({ name: 'track', size: 100, type: 'audio/mpeg' }), '')
})
test('audio timestamps are bounded and file fingerprints distinguish modified files', () => {
  assert.equal(audio.audioTime(NaN), '00:00')
  assert.equal(audio.audioTime(-1), '00:00')
  assert.equal(audio.audioTime(65.7), '01:05')
  assert.equal(audio.audioTime(3600), '60:00')
  assert.notEqual(audio.audioFingerprint({ name: 'a.wav', size: 10, lastModified: 1 }),
    audio.audioFingerprint({ name: 'a.wav', size: 10, lastModified: 2 }))
})
test('every bundled sound has an illustration and a non-silent, bounded PCM loop', () => {
  assert.equal(audio.builtInTracks.length, 8)
  assert.equal(new Set(audio.builtInTracks.map(track => track.id)).size, 8)
  for (const track of audio.builtInTracks) {
    const wav = readFileSync(new URL(`../public${track.source}`, import.meta.url))
    assert.equal(wav.toString('ascii', 0, 4), 'RIFF')
    assert.equal(wav.toString('ascii', 8, 12), 'WAVE')
    assert.equal(wav.readUInt16LE(22), 1)
    const rate = wav.readUInt32LE(24)
    const duration = (wav.length - 44) / (rate * 2)
    assert.ok(duration >= 20 && duration <= 30)
    let squared = 0
    let peak = 0
    for (let i = 44; i < wav.length; i += 2) {
      const sample = wav.readInt16LE(i)
      squared += sample ** 2
      peak = Math.max(peak, Math.abs(sample))
    }
    assert.ok(Math.sqrt(squared / ((wav.length - 44) / 2)) > 100, `${track.id} is non-silent`)
    assert.ok(peak < 30000, `${track.id} does not clip`)
    assert.ok(statSync(new URL(`../public${track.cover}`, import.meta.url)).size > 1000)
  }
})
