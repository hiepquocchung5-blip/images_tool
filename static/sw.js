const CACHE_NAME = 'vectorai-pwa-v5';
const urlsToCache = [
  '/',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
];

// Install and Cache
self.addEventListener('install', event => {
  self.skipWaiting(); // Force activate new service worker
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[PWA] Caching UI assets');
        return cache.addAll(urlsToCache);
      })
  );
});

// Clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[PWA] Clearing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// NETWORK-FIRST STRATEGY: Always fetch fresh, fallback to cache if offline
self.addEventListener('fetch', event => {
  // Ignore API calls and POST requests
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
      return;
  }
  
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // If network fetch is successful, clone it to cache and return
        const resClone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
        return response;
      })
      .catch(() => {
        // If network fails (offline), load from cache
        console.log('[PWA] Network failed, serving from cache');
        return caches.match(event.request);
      })
  );
});