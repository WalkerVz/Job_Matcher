const CACHE_NAME = 'career-radar-v7';

// Aset statis yang boleh di-cache (UI shell)
// Gunakan path relatif agar kompatibel di root domain (/) maupun subpath (/Job_Matcher/)
const STATIC_ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './icon.svg',
  './manifest.json'
];

// Deteksi file data pekerjaan secara akurat (tidak bergantung pada subpath/domain)
function isDataRequest(url) {
  const pathname = url.pathname.toLowerCase();
  return (
    pathname.endsWith('matched_jobs.json') ||
    pathname.endsWith('matched_jobs.js') ||
    pathname.endsWith('last_updated.json') ||
    pathname.endsWith('new_jobs.json')
  );
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Gunakan Promise.allSettled agar kegagalan 1 aset opsional tidak menggagalkan seluruh install
      return Promise.allSettled(
        STATIC_ASSETS.map((asset) => cache.add(asset).catch((err) => {
          console.warn('[SW] Cache add warning for asset:', asset, err);
        }))
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log('[SW] Deleting stale cache:', name);
            return caches.delete(name);
          }
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Abaikan request non-GET
  if (event.request.method !== 'GET') return;

  // File data: SELALU network-only dengan cache: 'no-store'
  // JANGAN PERNAH simpan di CacheStorage agar data lowongan selalu fresh dan sinkron
  if (isDataRequest(url)) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' }).catch(() => {
        // Fallback hanya jika perangkat offline total
        return caches.match(event.request);
      })
    );
    return;
  }

  // Aset statis: network-first, update cache di background
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      })
      .catch(() => caches.match(event.request))
  );
});
