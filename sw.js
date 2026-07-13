const CACHE_NAME = 'career-radar-v5';

// Aset statis yang boleh di-cache (UI shell)
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/app.js',
  '/icon.svg',
  '/manifest.json'
];

// File data — JANGAN di-cache statis, selalu ambil dari network
const DATA_FILES = [
  '/matched_jobs.js',
  '/matched_jobs.json',
  '/last_updated.json',
  '/new_jobs.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) return caches.delete(name);
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  const isDataFile = DATA_FILES.some((f) => url.pathname.startsWith(f.split('?')[0]));

  if (isDataFile) {
    // Data job: selalu network-first, TIDAK disimpan ke cache
    // Sehingga setiap buka app, data selalu fresh dari server
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // Aset statis: network-first, update cache di background
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (event.request.method === 'GET' && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});
