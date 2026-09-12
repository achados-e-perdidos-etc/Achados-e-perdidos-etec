const CACHE_NAME = 'etec-achados-v2';
const ASSETS = [
    '/',
    '/style.css',
    '/script.js',
    '/logo.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then((cache) => cache.addAll(ASSETS))
        .catch((err) => console.log('Erro ao fazer cache PWA:', err))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
        .then((response) => response || fetch(event.request))
    );
});
