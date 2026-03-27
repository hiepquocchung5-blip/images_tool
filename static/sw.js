const CACHE_NAME = 'vectorai-pwa-v1';
const urlsToCache = [
  '/',
  '/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
];

// Install the Service Worker and cache the core UI assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened PWA cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Intercept network requests
self.addEventListener('fetch', event => {
  // Do NOT cache the AI API requests (we always want fresh processing)
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
      return;
  }
  
  // Serve cached UI for faster loads, otherwise fetch from internet
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response; 
        }
        return fetch(event.request);
      })
  );
});

// Clean up old caches on update
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});