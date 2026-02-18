/*
  Service Worker — handles caching and offline support.
  
  Strategy: "Network First, Cache Fallback"
  - Always try to fetch fresh data from the network
  - If offline, serve from cache
  - Static assets (HTML, CSS, fonts) are pre-cached on install
  
  We DON'T cache API responses aggressively because the dashboard
  shows real-time data — stale cache would be misleading.
*/

const CACHE_NAME = 'audimeta-dash-v1';

// Assets to pre-cache on install
const PRECACHE_URLS = [
    '/',
    '/static/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
];

// Install: pre-cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activate: clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch: network first, cache fallback
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // For API calls: network only (we want fresh data)
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() =>
                new Response(JSON.stringify([]), {
                    headers: { 'Content-Type': 'application/json' }
                })
            )
        );
        return;
    }

    // For everything else: network first, cache fallback
    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
