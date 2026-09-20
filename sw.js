// ==============================================================================
// SERVICE WORKER - ETEC ACHADOS E PERDIDOS (VERSÃO 2.0 PWA & WEB PUSH)
// ==============================================================================

const CACHE_NAME = 'etec-achados-v2';

const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/script.js',
    '/logo.png',
    '/logo_secretaria.png',
    '/manifest.json',
    '/icon-192.png',
    '/icon-512.png'
];

// INSTALAÇÃO: Armazena em cache os recursos estáticos essenciais
self.addEventListener('install', (e) => {
    self.skipWaiting();
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
    );
});

// ATIVAÇÃO: Invalida caches obsoletos
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

// INTERCEPTAÇÃO DE REDE: Estratégia Network-First para a API e Stale-While-Revalidate para estáticos
self.addEventListener('fetch', (e) => {
    // Nunca interceptar chamadas da API REST ou autenticação Google
    if (e.request.url.includes('/api/') || e.request.url.includes('googleapis.com') || e.request.url.includes('accounts.google.com')) {
        return;
    }

    e.respondWith(
        fetch(e.request).catch(() => {
            return caches.match(e.request).then((res) => {
                if (res) return res;
                if (e.request.mode === 'navigate') {
                    return caches.match('/index.html');
                }
            });
        })
    );
});

// ==============================================================================
// RECEBIMENTO DE NOTIFICAÇÕES WEB PUSH (TELA DE BLOQUEIO / SISTEMA OPERACIONAL)
// ==============================================================================
self.addEventListener('push', (event) => {
    let payload = {
        title: 'ETEC Achados e Perdidos',
        body: 'Você tem uma nova notificação sobre seus pertences.',
        url: '/',
        icon: '/icon-192.png'
    };

    if (event.data) {
        try {
            const parsed = event.data.json();
            payload = { ...payload, ...parsed };
        } catch (err) {
            payload.body = event.data.text();
        }
    }

    const options = {
        body: payload.body,
        icon: payload.icon || '/icon-192.png',
        badge: '/icon-192.png',
        vibrate: [150, 50, 150],
        data: {
            url: payload.url || '/'
        },
        actions: [
            { action: 'abrir', title: 'Ver Pertence' },
            { action: 'fechar', title: 'Dispensar' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(payload.title, options)
    );
});

// CLIQUE NA NOTIFICAÇÃO
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'fechar') return;

    const urlAlvo = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (let client of windowClients) {
                if ('focus' in client) {
                    client.navigate(urlAlvo);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlAlvo);
            }
        })
    );
});
