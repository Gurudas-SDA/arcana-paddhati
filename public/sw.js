// Arcana-paddhati service worker (v5) — the whole book offline, robust updates.
//
// MAIN RULE (Satkirti, 06.10.2026): the app works OFFLINE on iPad, iPhone,
// Android and computers after the first visit.
//
// After the app has been opened once online, every page (all languages), RSC
// payload, build asset, font, image, hotspot mask, search index and bundled
// transcript listed in precache-manifest.json (scripts/build-precache.mjs) is
// cached.
//
// Versioning (why v5): v4 called skipWaiting() at once, swallowed precache
// errors and deleted the previous cache on activate — so a deploy whose
// precache did not finish (app closed / network lost during the ~180 MB
// download) left a HALF-FILLED new cache and NO old one: offline the book did
// not open until the next online visit filled the rest. Now:
//   * a version is "complete" only when every manifest URL is in its cache
//     (marker entry COMPLETE_KEY); older caches are deleted ONLY then;
//   * while a newer worker has an incomplete cache and a complete older one
//     exists, its install fails on purpose (the old worker keeps serving; the
//     download resumes on the next visit — the cache is kept between tries);
//   * every lookup falls back to ANY Arcana cache (an old, complete version
//     serves offline whatever the new one still lacks);
//   * unchanged files are copied from the previous version's cache (per-file
//     hashes in the manifest) instead of being downloaded again;
//   * offline navigation to a page never cached answers with the language's
//     cover / the start page / a small offline notice — never the browser's
//     error page.
const VERSION = '__PRECACHE_VERSION__';
const BASE = '/arcana-paddhati/';
const START_URL = BASE;
const CACHE_PREFIX = 'arcana-paddhati-';
const CACHE_NAME = CACHE_PREFIX + (VERSION.startsWith('__') ? 'dev' : VERSION);
const MANIFEST_URL = BASE + 'precache-manifest.json';
const COMPLETE_KEY = BASE + '__precache-complete__';
const MANIFEST_KEY = BASE + '__precache-manifest__';
// Non-default languages live under /arcana-paddhati/<code>/ (lib/languages.json).
const LANG_CODES = ['ru', 'ru-iast', 'lv', 'de', 'fr', 'es', 'it', 'uk', 'hu'];
const NETWORK_TIMEOUT_MS = 3000;
const CONCURRENCY = 6;
const RETRIES = 3;
const TOPUP_INTERVAL_MS = 2 * 60 * 1000;
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
// `_rsc` cache-busting query and an `RSC: 1` header.
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

async function arcanaCacheNames() {
  return (await caches.keys()).filter((k) => k.startsWith(CACHE_PREFIX));
}

// This version first, then any other (older) Arcana cache.
async function cacheMatch(key) {
  const own = await (await caches.open(CACHE_NAME)).match(key, MATCH_OPTS);
  if (own) return own;
  for (const name of await arcanaCacheNames()) {
    if (name === CACHE_NAME) continue;
    const hit = await (await caches.open(name)).match(key, MATCH_OPTS);
    if (hit) return hit;
  }
  return undefined;
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

async function isComplete(name) {
  const cache = await caches.open(name);
  const mark = await cache.match(COMPLETE_KEY);
  return !!mark;
}

// A complete Arcana cache other than this version's (the one still serving).
async function completeOlderCache() {
  for (const name of await arcanaCacheNames()) {
    if (name !== CACHE_NAME && (await isComplete(name))) return name;
  }
  return null;
}

async function dropOlderCaches() {
  for (const name of await arcanaCacheNames()) {
    if (name !== CACHE_NAME) await caches.delete(name);
  }
}

// ---------- precache ----------

async function fetchWithRetry(url) {
  let lastError;
  for (let attempt = 0; attempt < RETRIES; attempt++) {
    if (isOffline()) throw new Error('offline');
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

// Hash map {url: hash} of a cache's manifest (stored at precache time).
async function storedHashes(name) {
  try {
    const res = await (await caches.open(name)).match(MANIFEST_KEY);
    if (!res) return {};
    const m = await res.json();
    const out = {};
    (m.urls || []).forEach((u, i) => { if (m.hashes && m.hashes[i]) out[u] = m.hashes[i]; });
    return out;
  } catch {
    return {};
  }
}

let precacheRunning = null;
// Older caches may be dropped only by the ACTIVE worker (while installing,
// the previous worker still serves from them).
let activated = false;
// Add every manifest URL not yet in this version's cache. Resumable: an
// interrupted run keeps what it fetched, the next run fills the rest.
function precacheAll() {
  if (!precacheRunning) {
    precacheRunning = doPrecache().finally(() => { precacheRunning = null; });
  }
  return precacheRunning;
}

async function doPrecache() {
  const cache = await caches.open(CACHE_NAME);
  if (await cache.match(COMPLETE_KEY)) {
    return { total: 0, fetched: 0, copied: 0, failed: 0, complete: true };
  }
  let manifest;
  try {
    const res = await fetch(MANIFEST_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('manifest ' + res.status);
    manifest = await res.json();
  } catch {
    // Manifest unavailable (offline / dev server): nothing more to do now.
    return { total: 0, fetched: 0, copied: 0, failed: 1, complete: false };
  }
  if (!VERSION.startsWith('__') && manifest.version !== VERSION) {
    // A newer deploy is already online: this worker is outdated, the browser
    // will install the new one. Do not mix versions in this cache.
    return { total: 0, fetched: 0, copied: 0, failed: 1, complete: false, stale: true };
  }
  const urls = manifest.urls || [];
  const hashes = manifest.hashes || [];
  // Unchanged files: copy from an older version's cache.
  const older = [];
  for (const name of await arcanaCacheNames()) {
    if (name !== CACHE_NAME) older.push({ cache: await caches.open(name), hashes: await storedHashes(name) });
  }
  const missing = [];
  for (let i = 0; i < urls.length; i++) {
    if (!(await cache.match(urls[i], MATCH_OPTS))) missing.push(i);
  }
  let failed = 0;
  let fetched = 0;
  let copied = 0;
  let next = 0;
  async function worker() {
    while (next < missing.length) {
      const i = missing[next++];
      const url = urls[i];
      try {
        let res = null;
        if (hashes[i]) {
          for (const o of older) {
            if (o.hashes[url] === hashes[i]) {
              res = await o.cache.match(url, MATCH_OPTS);
              if (res) break;
            }
          }
        }
        if (res) {
          await cache.put(url, res);
          copied++;
        } else {
          await cache.put(url, await fetchWithRetry(url));
          fetched++;
        }
      } catch {
        failed++;
      }
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  const complete = failed === 0;
  if (complete) {
    await cache.put(MANIFEST_KEY, new Response(JSON.stringify(manifest), { headers: { 'Content-Type': 'application/json' } }));
    await cache.put(COMPLETE_KEY, new Response(VERSION));
    // Only now is the previous version no longer needed.
    if (activated) await dropOlderCaches();
  }
  return { total: urls.length, fetched, copied, failed, complete };
}

// Re-run precache occasionally while online, to fill URLs that failed.
let lastTopUp = 0;
function topUp() {
  if (precacheRunning || isOffline() || Date.now() - lastTopUp < TOPUP_INTERVAL_MS) return precacheRunning;
  lastTopUp = Date.now();
  return precacheAll().catch(() => {});
}

// ---------- lifecycle ----------

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const status = await precacheAll().catch(() => ({ complete: false }));
    lastTopUp = Date.now();
    if (!status.complete && (await completeOlderCache())) {
      // Keep the complete older version in charge; the download resumes on
      // the next visit (this cache is kept). Failing install is on purpose.
      throw new Error('precache incomplete — keeping the previous version');
    }
    // First install (nothing older) or complete: take over at once.
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  activated = true;
  event.waitUntil((async () => {
    if (await isComplete(CACHE_NAME)) await dropOlderCaches();
    await self.clients.claim();
  })());
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

function offlinePage(url) {
  const ru = /\/(ru|ru-iast|uk)\//.test(url.pathname);
  const text = ru
    ? 'Эта страница ещё не сохранена для чтения без интернета. Откройте книгу один раз с интернетом.'
    : 'This page is not yet stored for offline reading. Open the book once with internet.';
  return new Response(
    `<!doctype html><html lang="${ru ? 'ru' : 'en'}" translate="no"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` +
      `<title>Арчана-паддхати</title><body style="font-family:Georgia,serif;background:#FDF8F0;color:#2C1810;padding:24px;line-height:1.6">` +
      `<p>${text}</p><p><a href="${BASE}" style="color:#8B6508">‹ ${ru ? 'К книге' : 'To the book'}</a></p></body></html>`,
    { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

// Navigations: network-first (short timeout), then the cached page (any
// version), then the language home, then the start page, then a notice.
async function handleNavigation(event, url) {
  const key = pageKey(url);
  // A page never cached: go to (redirect, so the URL matches the page) the
  // language's cover, else the start page, else a small notice.
  const fallback = async () => {
    const page = await cacheMatch(key);
    if (page) return page;
    for (const home of [langHome(url), START_URL]) {
      if (home !== key && (await cacheMatch(home))) return Response.redirect(home, 302);
    }
    return offlinePage(url);
  };
  if (isOffline()) return fallback();
  const net = fetch(event.request);
  try {
    const res = await Promise.race([
      net,
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), NETWORK_TIMEOUT_MS)),
    ]);
    if (res.ok) {
      cachePut(key, res);
      event.waitUntil(topUp() || Promise.resolve());
      return res;
    }
    // 404 / 5xx online: a cached copy is better than an error page.
    return (await cacheMatch(key)) || res;
  } catch {
    const cached = await cacheMatch(key);
    if (cached) return cached;
    try {
      const res = await net;
      if (res.ok) return res;
    } catch {
      // still no network
    }
    return fallback();
  }
}

// RSC payloads: cache by path (the `_rsc` query is a cache-buster).
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

// Content-hashed build assets never change: cache-first (any version).
async function handleStatic(request, url) {
  const cached = await cacheMatch(url.pathname);
  if (cached) return cached;
  const res = await fetch(request);
  cachePut(url.pathname, res);
  return res;
}

// Everything else (search indexes, images, icons, transcripts): network-first.
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
