const CACHE = 'h5-v13';
const SHELL = [
  './',
  './index.html',
  './Budapest_H5_HÉV.svg.png',
  './favicon.ico',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Network-only for live API, map tiles, and CDN libraries
  if (
    url.hostname === 'futar.bkk.hu' ||
    url.hostname.includes('cartocdn') ||
    url.hostname.includes('unpkg') ||
    url.hostname.includes('openstreetmap')
  ) {
    e.respondWith(fetch(e.request));
    return;
  }
  // Cache-first for app shell
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
