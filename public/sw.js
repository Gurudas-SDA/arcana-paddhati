// Arcana-paddhati service worker (v6) — the whole book offline, robust updates.
//
// v6 (Reader v7.1, 06.10.2026): Android Chrome stopped the v5 install (one
// ~180 MB / ~1900-file waitUntil) after ~300 s and nothing was offline. Now
// the install caches only the CORE — app shell + every chapter page and RSC
// payload of the reader's language (ru-iast always, plus the language of the
// open page) — and takes over at once; the rest (other languages,
// transcripts) is fetched in the background after activation, resumable
// (cached files are skipped), continued on every page view (the page pings
// the worker), with progress messages to the pages. An older complete cache
// is kept until the new one is complete.
//
// КСВ 15.10.2026 (iPad: a tapped chapter stayed «загружается» over the cover
// while «Книга сохраняется… 76 %»): the reader first — RSC payloads, pictures
// and search indexes this version has stored are answered from the device at
// once, and the
// background download starts no new file while a page request waits for the
// network. (The release re-downloaded the whole book because Next.js's random
// build id changed every page: scripts/stable-build-id.mjs.)
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
// The app's base = the folder of this script: '/arcana-paddhati/' in
// production, '/arcana-paddhati/staging/' for the staging build (same origin,
// branch `staging`). Each has its own scope and its own caches.
const BASE = new URL('./', self.location.href).pathname;
const START_URL = BASE;
// Production keeps 'arcana-paddhati-' (existing caches stay valid); staging
// gets 'arcana-paddhati_staging-', which does NOT start with the production
// prefix — so neither worker reads or deletes the other's caches.
const CACHE_PREFIX = BASE.replace(/^\/|\/$/g, '').split('/').join('_') + '-';
// Other builds published below this one (production's scope contains
// /arcana-paddhati/staging/): this worker never handles their requests.
const NESTED_APPS = ['staging/'];
const CACHE_NAME = CACHE_PREFIX + (VERSION.startsWith('__') ? 'dev' : VERSION);
const MANIFEST_URL = BASE + 'precache-manifest.json';
const COMPLETE_KEY = BASE + '__precache-complete__';
const MANIFEST_KEY = BASE + '__precache-manifest__';
// Non-default languages live under /arcana-paddhati/<code>/ (lib/languages.json).
const LANG_CODES = ['ru', 'ru-iast', 'lv', 'de', 'fr', 'es', 'it', 'uk', 'hu', 'pt', 'lt'];
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
function langCode(pathname) {
  return pathname.startsWith(BASE) ? pathname.slice(BASE.length).split('/')[0] : '';
}

function langHome(url) {
  const code = langCode(url.pathname);
  return LANG_CODES.includes(code) ? BASE + code + '/' : START_URL;
}

// ---------- cache helpers ----------

async function arcanaCacheNames() {
  return (await caches.keys()).filter((k) => k.startsWith(CACHE_PREFIX));
}

// This version's own cache only (all its files belong to this build).
async function ownMatch(key) {
  return (await caches.open(CACHE_NAME)).match(key, MATCH_OPTS);
}

// This version first, then any other (older) Arcana cache.
async function cacheMatch(key) {
  const own = await ownMatch(key);
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

// КСВ 15.10.2026 (iPad: «1.2. Совершите омовение» stayed «загружается» while the
// book was being saved, 76 %): the reader's own requests first. While a page
// waits for the network, the background download starts no new file.
let foreground = 0;
function foregroundFetch(request) {
  foreground++;
  const done = () => { foreground--; };
  const p = fetch(request);
  p.then(done, done);
  return p;
}
async function foregroundIdle() {
  for (let i = 0; foreground > 0 && i < 150; i++) await new Promise((r) => setTimeout(r, 100));
}

function fetchWithTimeout(request, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout')), ms);
    foregroundFetch(request).then(
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
    await foregroundIdle();
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
    precacheRunning = doPrecache(null).finally(() => { precacheRunning = null; });
  }
  return precacheRunning;
}

// Languages of the open pages ("en" for the root pages).
async function clientLangs() {
  const out = new Set(['ru-iast']);
  try {
    for (const c of await self.clients.matchAll({ includeUncontrolled: true, type: 'window' })) {
      const path = new URL(c.url).pathname;
      if (!(path + '/').startsWith(BASE) || NESTED_APPS.some((n) => path.startsWith(BASE + n))) continue;
      const code = langCode(path);
      out.add(LANG_CODES.includes(code) ? code : 'en');
    }
  } catch {
    // no clients API
  }
  return out;
}

// Only the core: shell + the given languages (install step).
function precacheCore(langs) {
  return doPrecache((group) => group === 'shell' || langs.has(group));
}

// 20.10.2026 (Vraja Lila msg 5318, «Видимая загрузка», commit 1): the progress
// message also carries the failures — how many files could not be stored and
// of which kind — so the page can say «Сохранено не всё» and what is missing
// (before, `failed` was counted here and lost).
function failKind(url) {
  const path = url.split('?')[0];
  if (path.startsWith(BASE + 'transcripts/')) return 'transcripts';
  if (/\.(webp|png|jpe?g|gif|svg|avif|ico)$/i.test(path)) return 'images';
  if (path.endsWith('/') || path.endsWith('.txt') || /\/search-index\.[a-z-]+\.json$/.test(path)) return 'text';
  return 'other';
}

let lastProgress = 0;
async function postProgress(done, total, final, failed = 0, failedKinds = {}) {
  const now = Date.now();
  if (!final && now - lastProgress < 1500) return;
  lastProgress = now;
  try {
    for (const c of await self.clients.matchAll({ type: 'window' })) {
      c.postMessage({
        type: 'precache-progress', version: VERSION, done, total,
        complete: !!final && done >= total && !failed, failed, failedKinds, final: !!final,
      });
    }
  } catch {
    // ignore
  }
}

async function doPrecache(only) {
  const cache = await caches.open(CACHE_NAME);
  if (await cache.match(COMPLETE_KEY)) {
    // Already whole: tell the page (a page that saw an unfinished download
    // must learn that it is done, without a new download run).
    if (!only) postProgress(0, 0, true);
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
  const groups = manifest.groups || [];
  // Unchanged files: copy from an older version's cache.
  const older = [];
  for (const name of await arcanaCacheNames()) {
    if (name !== CACHE_NAME) older.push({ cache: await caches.open(name), hashes: await storedHashes(name) });
  }
  const missing = [];
  let have = 0;
  for (let i = 0; i < urls.length; i++) {
    if (only && !only(groups[i] || 'shell')) continue;
    if (!(await cache.match(urls[i], MATCH_OPTS))) missing.push(i);
    else have++;
  }
  const scope = have + missing.length;
  let failed = 0;
  const failedKinds = {};
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
        const kind = failKind(url);
        failedKinds[kind] = (failedKinds[kind] || 0) + 1;
      }
      if (!only) postProgress(have + fetched + copied, scope, false, failed, failedKinds);
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  if (only) return { total: scope, fetched, copied, failed, complete: false, core: failed === 0 };
  postProgress(have + fetched + copied, scope, true, failed, failedKinds);
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

// 20.10.2026 (Vraja Lila msg 5316 p. 2; Satkirti's iPad showed the old
// Panca-tattva): the new version takes over even when part of its files is not
// downloaded yet. Before, an incomplete core made the install fail on purpose
// and the OLD worker kept serving the old book until the new one was complete —
// on a slow network for days. Nothing is lost offline: every lookup falls back
// to the older complete cache (cacheMatch), which is deleted only when this
// version is complete; the rest is fetched in the background as before.
self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    // Only the core here (small, well within the browser's install time); an
    // unfinished core continues in the background after activation.
    await precacheCore(await clientLangs()).catch(() => ({ core: false }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  activated = true;
  event.waitUntil((async () => {
    if (await isComplete(CACHE_NAME)) await dropOlderCaches();
    await self.clients.claim();
  })());
  // The rest in the background (not inside activate: fetches must not wait).
  lastTopUp = Date.now();
  precacheAll().catch(() => {});
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'precache-continue') {
    // A page is open: keep filling the cache (resumable; each message gives
    // the worker a new lifetime for the download).
    lastTopUp = Date.now();
    event.waitUntil(precacheAll().catch(() => {}));
    return;
  }
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
  // Offline: the stored page at once.
  if (isOffline()) return fallback();
  // Online: network first, so a page of a new release is the new page (Vraja
  // Lila msg 5316 p. 2: the short wait is for offline only — before, a stored
  // page of THIS version was answered after a 1 s wait even online, and
  // after a release the reader kept getting the stored old page). The network
  // gets NETWORK_TIMEOUT_MS; the background download yields to it meanwhile
  // (foregroundIdle). Only then the stored copy.
  const net = foregroundFetch(event.request);
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
  // This version's payload: from the device at once (КСВ 15.10.2026 — a tapped
  // chapter waited up to 3 s per payload for a network busy with the background
  // download). Normally the page is of the same build; if the page is newer
  // (a release not yet installed here), Next.js sees the other build id in the
  // payload and loads the page as a whole instead (handleNavigation).
  const own = await ownMatch(key);
  if (own) return own;
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
  const res = await foregroundFetch(request);
  cachePut(url.pathname, res);
  return res;
}

// Everything else (search indexes, images, icons, transcripts): network-first.
async function handleOther(request, url) {
  // Stored by this version (pictures, search index, transcripts): at once.
  const own = await ownMatch(url.pathname);
  if (own) return own;
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
  if (NESTED_APPS.some((n) => (url.pathname + '/').startsWith(BASE + n))) return;
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
