// Notifications only: never cache account responses or run a background timer.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()))
self.addEventListener('notificationclick', event => {
  event.notification.close()
  const data = event.notification.data || {}
  const href = typeof data.href === 'string' && /^\/index(?:\?|$)/.test(data.href) ? data.href : '/index'
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const client = windows.find(item => new URL(item.url).origin === self.location.origin)
    if (client) {
      await client.focus()
      client.postMessage({ type: 'smarttodo-reminder-open', href, owner: data.owner })
    } else await self.clients.openWindow(href)
  })())
})
