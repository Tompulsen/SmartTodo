import { reactive } from 'vue'
import { auth, authRequest } from '@/auth'
import { apiFetch } from '@/http'
import { locationError } from './weather'

interface SharingReply { enabled: boolean; token: string | null; receivedAt: string | null }
export const locationSharing = reactive({
  active: false, busy: false, tracking: false, error: '', receivedAt: null as string | null,
  position: null as GeolocationPosition | null
})
const options = { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }
let token: string | null = null
let generation = 0
let watchId: number | null = null
let timer: ReturnType<typeof setInterval> | null = null
let pendingGeneration: number | null = null
let lastSend = 0

function stopWatching() {
  if (watchId !== null) navigator.geolocation?.clearWatch(watchId)
  watchId = null
  if (timer) clearInterval(timer)
  timer = null
  locationSharing.tracking = false
}
async function revoke(sessionToken: string) {
  try {
    await apiFetch('/api/environment/location/stop', {
      method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: sessionToken })
    })
  } catch { /* An offline device cannot revoke immediately; the server expires old fixes. */ }
}
export function endLocationSession() {
  ++generation
  stopWatching()
  locationSharing.active = false
  locationSharing.busy = false
  locationSharing.position = null
  locationSharing.receivedAt = null
  document.removeEventListener('visibilitychange', visibilityChanged)
  window.removeEventListener('pagehide', endLocationSession)
  if (token) void revoke(token)
  token = null
}
async function sendPosition(position: GeolocationPosition, version: number) {
  if (version !== generation || !locationSharing.active || document.hidden) return
  if (auth.localMode) {
    locationSharing.position = position
    locationSharing.tracking = true
    return
  }
  if (!token || pendingGeneration === version || Date.now() - lastSend < 10000) return
  pendingGeneration = version
  try {
    const result = await authRequest<{ receivedAt: string }>('/api/environment/location', 'POST', {
      token, latitude: position.coords.latitude, longitude: position.coords.longitude,
      accuracy: position.coords.accuracy, capturedAt: position.timestamp
    })
    if (version !== generation) return
    lastSend = Date.now()
    locationSharing.position = position
    locationSharing.receivedAt = result.receivedAt
    locationSharing.error = ''
    locationSharing.tracking = true
  } catch (failure) {
    if (version !== generation) return
    locationSharing.error = failure instanceof Error ? failure.message : '位置更新失败，请重新进入。'
    endLocationSession()
  } finally { if (pendingGeneration === version) pendingGeneration = null }
}
function startWatching() {
  stopWatching()
  if (!locationSharing.active || document.hidden) return
  locationSharing.tracking = !!locationSharing.position
  const version = generation
  const success = (position: GeolocationPosition) => { void sendPosition(position, version) }
  const failure = (error: GeolocationPositionError) => {
    if (version !== generation) return
    locationSharing.error = locationError(error)
    endLocationSession()
  }
  watchId = navigator.geolocation.watchPosition(success, failure, options)
  timer = setInterval(() => navigator.geolocation.getCurrentPosition(success, failure, options), 30000)
}
function visibilityChanged() {
  if (document.hidden) stopWatching()
  else startWatching()
}
export async function beginLocationSession() {
  if (locationSharing.busy || locationSharing.active) return false
  const version = ++generation
  locationSharing.busy = true
  locationSharing.error = ''
  try {
    if (!window.isSecureContext || !navigator.geolocation) {
      throw new Error('此浏览器无法定位，请通过 HTTPS 使用支持定位的浏览器。')
    }
    // Ask the browser only after the user accepts the visible feature notice.
    const position = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, error => reject(new Error(locationError(error))), options)
    })
    if (version !== generation) return false
    if (!auth.localMode) {
      const result = await authRequest<SharingReply>('/api/environment/location', 'PATCH', { enabled: true })
      if (version !== generation) {
        if (result.token) void revoke(result.token)
        return false
      }
      token = result.token
    }
    locationSharing.active = true
    lastSend = 0
    await sendPosition(position, version)
    if (version !== generation || !locationSharing.active) return false
    document.addEventListener('visibilitychange', visibilityChanged)
    window.addEventListener('pagehide', endLocationSession)
    startWatching()
    return true
  } catch (failure) {
    if (version === generation) {
      locationSharing.error = failure instanceof Error ? failure.message : '定位失败，请重试。'
      endLocationSession()
    }
    return false
  } finally { if (version === generation) locationSharing.busy = false }
}
