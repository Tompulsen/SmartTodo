export let isLocalMode = false

export async function detectLocalMode(): Promise<void> {
  isLocalMode = false
  try {
    const response = await fetch('/_local/health', {
      signal: AbortSignal.timeout(3000)
    })
    if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
      return
    }

    const health = await response.json()
    isLocalMode =
      health?.application === 'SmartTodo' &&
      health?.mode === 'local' &&
      health?.authentication_required === false
  } catch {
    // Regular deployments have no local endpoint and keep their login flow.
  }
}
