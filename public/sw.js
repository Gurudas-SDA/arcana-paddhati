// Arcana Paddhati service worker (v4) — full offline book.
//
// After the app has been opened once online, every page, RSC payload, build
// asset, search index and image listed in precache-manifest.json (written by
// scripts/build-precache.mjs at postbuild) is cached, so the whole book works
// offline: all sections, all languages, client-side navigation and search.
//
// VERSION is stamped in at postbuild (hash of all precached files), so every
// content change produces a byte-different sw.js -> the browser installs the
// new worker, which precaches into a fresh cache and drops the old one.
const VERSION = '__PRECACHE_VERSION__';
const BASE = '/arcana-paddhati/';
const START_URL = BASE;
const CACHE_PREFIX = 'arcana-paddhati-';
const CACHE_NAME = CACHE_PREFIX + (VERSION.startsWith('__') ? 'dev' : VERSION);
const MANIFEST_URL = BASE + 'precache-manifest.json';
// Non-default languages live under /arcana-paddhati/<code>/ (lib/languages.json).
const LANG_CODES = ['ru', 'ru-iast', 'lv', 'de', 'fr', 'es', 'it', 'uk'];
const NETWORK_TIMEOUT_MS = 3000;
const CONCURRENCY = 6;
const RETRIES = 3;
const TOPUP_INTERVAL_MS = 5 * 60 * 1000;
const MATCH_OPTS = { ignoreSearch: true, ignoreVary: true };

// ---------- URL normalisation (pure; mirrored by the offline test) ----------

// Cache key of a page: directory URL with trailing slash, no query/hash,
// "index.html" stripped. "/arcana-paddhati/ru/offering-bhoga?x#y" ->
// "/arcana-paddhati/ru/offering-bhoga/".
function pageKey(url) {
  let path = url.pathname;
  if (path.endsWith('/index.html')) path = path.slice(0, -'index.html'.length);
  const last = path.slice(path.lastIndexOf('/') + 1);
  if (last && !last.includes('.')) path += '/';
  return path;
}

// RSC payloads in output:"export" mode are static .txt files fetched with an
// `_rsc` cache-busting query and an `RSC: 1` header:
//   <route>/index.txt?_rsc=…               (navigation, fetchServerResponse)
//   <route>/__next.<segment>.txt?_rsc=…    (segment prefetch)
function isRscRequest(request, url) {
  if (url.searchParams.has('_rsc')) return true;
  if (request.headers.get('RSC') === '1') return true;
  if (!url.pathname.endsWith('.txt')) return false;
  const name = url.pathname.slice(url.pathname.lastIndexOf('/') + 1);
  return name === 'index.txt' || url.pathname.includes('/__next.');
}

// Language home for an offline fallback: "/arcana-paddhati/ru/x/" -> "/arcana-paddhati/ru/".
function langHome(url) {
  const code = url.pathname.split('/')[2];
  return LANG_CODES.includes(code) ? BASE + code + '/' : START_URL;
}

// ---------- cache helpers ----------

function cacheMatch(key) {
  return caches.open(CACHE_NAME).then((cache) => cache.match(key, MATCH_OPTS));
}

function cachePut(key, response) {
  // Only complete, same-origin, non-redirected responses are reusable.
  if (!response || !response.ok || response.type !== 'basic' || response.redirected) return;
  const clone = response.clone();
  caches.open(CACHE_NAME).then((cache) => cache.put(key, clone)).catch(() => {});
}

function fetchWithTimeout(request, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout')), ms);
    fetch(request).then(
      (res) => { clearTimeout(timer); resolve(res); },
      (err) => { clearTimeout(timer); reject(err); }
    );
  });
}

function isOffline() {
  return self.navigator && self.navigator.onLine === false;
}

// ---------- precache ----------

async function fetchWithRetry(url) {
  let lastError;
  for (let attempt = 0; attempt < RETRIES; attempt++) {
    try {
      // Bypass the HTTP cache so a new version never stores stale files.
      const res = await fetch(new Request(url, { cache: 'reload', credentials: 'same-origin' }));
      if (res.ok && !res.redirected) return res;
      lastError = new Error(`HTTP ${res.status} ${url}`);
    } catch (err) {
      lastError = err;
    }
    await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
  }
  throw lastError;
}

// Add every manifest URL not yet in this version's cache. Resumable: an
// interrupted install keeps what it fetched, the next run fills the rest.
async function precacheAll() {
  const cache = await caches.open(CACHE_NAME);
  let urls = [START_URL];
  try {
    const res = await fetch(MANIFEST_URL, { cache: 'no-store' });
    if (res.ok) urls = (await res.json()).urls || urls;
  } catch {
    // Manifest unavailable (dev server / offline): keep the start page only.
  }
  const missing = [];
  for (const url of urls) {
    if (!(await cache.match(url, MATCH_OPTS))) missing.push(url);
  }
  let failed = 0;
  let next = 0;
  async function worker() {
    while (next < missing.length) {
      const url = missing[next++];
      try {
        await cache.put(url, await fetchWithRetry(url));
      } catch {
        failed++;
      }
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  return { total: urls.length, fetched: missing.length - failed, failed };
}

// Re-run precache occasionally while online, to fill URLs that failed at install.
let topUpRunning = null;
let lastTopUp = 0;
function topUp() {
  if (topUpRunning || isOffline() || Date.now() - lastTopUp < TOPUP_INTERVAL_MS) return topUpRunning;
  lastTopUp = Date.now();
  topUpRunning = precacheAll().catch(() => {}).finally(() => { topUpRunning = null; });
  return topUpRunning;
}

// ---------- lifecycle ----------

self.addEventListener('install', (event) => {
  self.skipWaiting();
  // Never let a failure block install; missing URLs are topped up later.
  event.waitUntil(precacheAll().then(() => { lastTopUp = Date.now(); }).catch(() => {}));
});

self.addEventListener('activate', (event) => {
  // Drop older Arcana caches only — other apps may share this origin (github.io).
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('arcana-paddhati') && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'precache-status') {
    event.waitUntil(
      precacheAll().then((status) => {
        if (event.source) event.source.postMessage({ type: 'precache-status', version: VERSION, ...status });
      })
    );
  }
});

// ---------- fetch strategies ----------

// Navigations: network-first (short timeout), then the cached page, then the
// language home, then the start page.
async function handleNavigation(event, url) {
  const key = pageKey(url);
  const fallback = async () =>
    (await cacheMatch(key)) || (await cacheMatch(langHome(url))) || (await cacheMatch(START_URL));
  if (isOffline()) return (await fallback()) || Response.error();
  const net = fetch(event.request);
  try {
    const res = await Promise.race([
      net,
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), NETWORK_TIMEOUT_MS)),
    ]);
    if (res.ok) {
      cachePut(key, res);
      event.waitUntil(topUp() || Promise.resolve());
    }
    return res;
  } catch {
    const cached = await fallback();
    if (cached) return cached;
    try { return await net; } catch { return Response.error(); }
  }
}

// RSC payloads: cache by path (the `_rsc` query is a cache-buster).
// Offline -> cache first; online -> network-first with timeout, cache fallback.
async function handleRsc(request, url) {
  const key = url.pathname;
  if (isOffline()) {
    const cached = await cacheMatch(key);
    if (cached) return cached;
  }
  try {
    const res = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
    if (res.ok) cachePut(key, res);
    return res;
  } catch {
    return (await cacheMatch(key)) || Response.error();
  }
}

// Content-hashed build assets never change: cache-first.
async function handleStatic(request, url) {
  const cached = await cacheMatch(url.pathname);
  if (cached) return cached;
  const res = await fetch(request);
  cachePut(url.pathname, res);
  return res;
}

// Everything else (search indexes, images, icons, manifest): network-first.
async function handleOther(request, url) {
  if (isOffline()) {
    const cached = await cacheMatch(url.pathname);
    if (cached) return cached;
  }
  try {
    const res = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
    if (res.ok) cachePut(url.pathname, res);
    return res;
  } catch {
    return (await cacheMatch(url.pathname)) || Response.error();
  }
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  // Only handle same-origin GET requests of this app; let the browser handle the rest.
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !(url.pathname + '/').startsWith(BASE)) return;
  if (url.pathname === BASE + 'sw.js' || url.pathname === MANIFEST_URL) return;
  if (request.headers.has('range')) return;

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(event, url));
  } else if (isRscRequest(request, url)) {
    event.respondWith(handleRsc(request, url));
  } else if (url.pathname.startsWith(BASE + '_next/static/')) {
    event.respondWith(handleStatic(request, url));
  } else {
    event.respondWith(handleOther(request, url));
  }
});
