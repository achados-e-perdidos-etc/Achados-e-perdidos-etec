self.addEventListener('install', (event) => {
    // Pula a espera e ativa o app imediatamente
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Interceptador simples para passar na validação rigorosa do Chrome
    event.respondWith(
        fetch(event.request).catch(() => {
            return new Response("Você está offline.");
        })
    );
});
