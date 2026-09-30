const CACHE_NAME = 'arcana-paddhati-v3';
const START_URL = '/arcana-paddhati/';
// Non-default languages live under /arcana-paddhati/<code>/ (lib/languages.json).
const LANG_CODES = ['ru', 'ru-iast', 'lv', 'de', 'fr', 'es', 'it', 'uk'];

// Offline fallback for a page that was never cached: the home page of the
// page's language if cached, else the start page.
function offlineFallback(url) {
  const code = url.pathname.split('/')[2];
  const langHome = LANG_CODES.includes(code) ? `/arcana-paddhati/${code}/` : null;
  return (langHome ? caches.match(langHome) : Promise.resolve(undefined))
    .then((cached) => cached || caches.match(START_URL));
}

self.addEventListener('install', (event) => {
  self.skipWaiting();
  // Precache the start page; never let a failure block install.
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.add(START_URL))
      .catch(() => {})
  );
});

self.addEventListener('activate', (event) => {
  // Drop old caches (e.g. v1) so stale content is not served.
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  // Only handle same-origin GET requests; let the browser handle the rest.
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Content-hashed build assets never change: cache-first.
  if (url.pathname.includes('/_next/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Everything else: network-first, cache as offline fallback.
  event.respondWith(
    fetch(request).then((response) => {
      if (response.ok) {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
      }
      return response;
    }).catch(() => {
      return caches.match(request).then((cached) => {
        if (cached) return cached;
        if (request.mode === 'navigate') return offlineFallback(url);
        return undefined;
      });
    })
  );
});
