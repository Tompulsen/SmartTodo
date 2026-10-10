let csrfToken = ''

export function setCsrfToken(value: string) { csrfToken = value }
export function getCsrfToken() { return csrfToken }

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (!['GET', 'HEAD', 'OPTIONS'].includes((init.method || 'GET').toUpperCase()) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' })
  if (response.status === 401 && !['/api/login', '/api/auth/register'].includes(path) && typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth-required'))
  }
  return response
}
