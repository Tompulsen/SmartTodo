export interface FocusTrack {
  id: string
  name: string
  cover: string
  source?: string
  file?: Blob
  duration?: number
  size?: number
  fingerprint?: string
  createdAt?: number
}

const tracks = [
  ['quiet', '轻柔白噪音'], ['music-box', '八音盒'], ['forest-rain', '林间细雨'], ['rain', '窗边小雨'],
  ['stream', '溪流潺潺'], ['ocean', '海边潮涌'], ['wind', '风吹麦浪'], ['clock', '时钟滴答']
]
export const builtInTracks: FocusTrack[] = tracks.map(([id, name]) => ({
  id: `builtin:${id}`, name, cover: `/focus-audio/${id}.png`, source: `/focus-audio/${id}.wav`
}))
export const MAX_AUDIO_SIZE = 50 * 1024 * 1024
export const MAX_LIBRARY_SIZE = 200 * 1024 * 1024
export const MAX_TRACKS = 20
export const AUDIO_PREFERENCES_KEY = 'smarttodo-focus-audio-v1'
export interface AudioPreferences { selectedId: string; volume: number; muted: boolean; loop: boolean }
export function parseAudioPreferences(raw: string | null): AudioPreferences {
  const defaults: AudioPreferences = { selectedId: '', volume: .5, muted: false, loop: true }
  try {
    const value = JSON.parse(raw || '{}')
    if (!value || typeof value !== 'object') return defaults
    return {
      selectedId: typeof value.selectedId === 'string' ? value.selectedId : '',
      volume: typeof value.volume === 'number' && Number.isFinite(value.volume) ? Math.min(1, Math.max(0, value.volume)) : .5,
      muted: value.muted === true,
      loop: value.loop !== false
    }
  } catch { return defaults }
}
export function audioTime(seconds: number) {
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0
  return `${Math.floor(value / 60).toString().padStart(2, '0')}:${(value % 60).toString().padStart(2, '0')}`
}
export function audioFileError(file: Pick<File, 'name' | 'size' | 'type'>): string {
  if (!file.size) return '这个文件是空的，请选择其他音频。'
  if (file.size > MAX_AUDIO_SIZE) return '单个音频不能超过 50 MB。'
  if (!/\.(mp3|wav|m4a|aac|ogg|oga|opus|flac|weba|webm)$/i.test(file.name) &&
      !file.type.startsWith('audio/')) return '请选择 MP3、WAV、M4A 等音频文件。'
  return ''
}
export function audioFingerprint(file: File) { return `${file.name}:${file.size}:${file.lastModified}` }

export function inspectAudio(file: File): Promise<number> {
  const invalid = audioFileError(file)
  if (invalid) return Promise.reject(new Error(invalid))
  return new Promise((resolve, reject) => {
    const audio = document.createElement('audio')
    const url = URL.createObjectURL(file)
    const timer = setTimeout(() => finish(new Error('音频读取超时，请换一个文件重试。')), 12000)
    function finish(error?: Error) {
      clearTimeout(timer)
      const duration = audio.duration
      audio.onloadedmetadata = null
      audio.onerror = null
      audio.removeAttribute('src')
      audio.load()
      URL.revokeObjectURL(url)
      if (error) reject(error)
      else resolve(duration)
    }
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => finish(Number.isFinite(audio.duration) && audio.duration > 0
      ? undefined : new Error('无法读取音频时长，请使用 MP3、WAV 或 M4A 文件。'))
    audio.onerror = () => finish(new Error('浏览器无法播放此文件，请检查格式或文件是否损坏。'))
    audio.src = url
  })
}

const DB_NAME = 'smarttodo-focus-audio'
const STORE = 'tracks'
function openLibrary(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) { reject(new Error('当前浏览器不支持保存本地音频。')); return }
    const request = indexedDB.open(DB_NAME, 1)
    let expired = false
    const timer = setTimeout(() => {
      expired = true
      reject(new Error('音频库打开超时，请关闭其他窗口后重试。'))
    }, 8000)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) request.result.createObjectStore(STORE, { keyPath: 'id' })
    }
    request.onsuccess = () => {
      clearTimeout(timer)
      if (expired) { request.result.close(); return }
      request.result.onversionchange = () => request.result.close()
      resolve(request.result)
    }
    request.onerror = () => { clearTimeout(timer); reject(new Error('无法打开本地音频库，请检查浏览器存储权限。')) }
  })
}
async function libraryTransaction<T>(mode: IDBTransactionMode,
  operation: (store: IDBObjectStore, result: (value: T) => void, fail: (message: string) => void) => void): Promise<T> {
  const db = await openLibrary()
  return new Promise<T>((resolve, reject) => {
    const transaction = db.transaction(STORE, mode)
    let value: T
    let message = ''
    const timer = setTimeout(() => {
      message = '音频保存超时，请重试。'
      transaction.abort()
    }, 15000)
    const cleanup = () => { clearTimeout(timer); db.close() }
    transaction.oncomplete = () => { cleanup(); resolve(value) }
    transaction.onabort = transaction.onerror = () => {
      cleanup()
      reject(new Error(message || (transaction.error?.name === 'QuotaExceededError'
        ? '浏览器存储空间不足，请删除部分本地音频后重试。' : '音频库操作失败，请检查存储权限后重试。')))
    }
    try {
      operation(transaction.objectStore(STORE), result => { value = result }, error => { message = error; transaction.abort() })
    } catch {
      message = '无法保存此音频，请重试。'
      transaction.abort()
    }
  })
}
export function loadLocalTracks(): Promise<FocusTrack[]> {
  return libraryTransaction('readonly', (store, result) => {
    const request = store.getAll()
    request.onsuccess = () => result((request.result as FocusTrack[])
      .filter(track => track.id.startsWith('local:') && track.file instanceof Blob)
      .sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)))
  })
}
export function saveLocalTrack(track: FocusTrack): Promise<void> {
  return libraryTransaction('readwrite', (store, result, fail) => {
    const request = store.getAll()
    request.onsuccess = () => {
      const tracks = request.result as FocusTrack[]
      if (tracks.some(item => item.fingerprint === track.fingerprint)) { fail('这个音频已经在本地音频库中。'); return }
      if (tracks.length >= MAX_TRACKS) { fail('最多保存 20 首本地音频，请先删除不需要的音频。'); return }
      if (tracks.reduce((sum, item) => sum + (item.file?.size || 0), 0) + (track.file?.size || 0) > MAX_LIBRARY_SIZE) {
        fail('本地音频库上限为 200 MB，请先删除部分音频。'); return
      }
      store.add(track)
      result(undefined)
    }
  })
}
export function deleteLocalTrack(id: string): Promise<void> {
  if (!id.startsWith('local:')) return Promise.reject(new Error('不能删除内置音频。'))
  return libraryTransaction('readwrite', (store, result) => { store.delete(id); result(undefined) })
}
