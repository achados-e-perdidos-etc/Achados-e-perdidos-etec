// ==============================================================================
// SERVICE WORKER - ETEC ACHADOS E PERDIDOS (VERSÃO 2.0 PWA & WEB PUSH)
// ==============================================================================

const CACHE_NAME = 'etec-achados-v28-404';

const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css',
    '/script.js',
    '/seguranca-interface.js',
    '/visao-formulario.js',
    '/acesso-portal.js',
    '/estado-fotos.js',
    '/estado-fotos.css',
    '/notificacoes-push.js',
    '/professores.js',
    '/central-notificacoes.js',
    '/meus-cadastros.js',
    '/rascunhos.js',
    '/movimento.css',
    '/melhorias-portal.css',
    '/acessibilidade.js',
    '/acessibilidade.css',
    '/upload-retomavel.js',
    '/404.html',
    '/jogo-404.css',
    '/jogo-404.js',

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
function urlNotificacao(valor) {
    try {
        const url = new URL(valor || '/', self.location.origin);
        if (url.origin === self.location.origin && !url.username && !url.password) return url.href;
    } catch (error) {}
    return self.location.origin + '/';
}

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
        body: typeof payload.body === 'string' ? payload.body.slice(0, 320) : 'Abra o portal para conferir.',
        icon: '/icon-192.png',
        badge: '/icon-192.png',
        tag: typeof payload.tag === 'string' ? payload.tag.slice(0, 100) : undefined,
        vibrate: [150, 50, 150],
        data: {
            url: urlNotificacao(payload.url)
        },
        actions: [
            { action: 'abrir', title: 'Abrir portal' },
            { action: 'fechar', title: 'Dispensar' }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(typeof payload.title === 'string' ? payload.title.slice(0, 100) : 'ETEC Achados e Perdidos', options)
    );
});

// CLIQUE NA NOTIFICAÇÃO
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'fechar') return;

    const urlAlvo = urlNotificacao(event.notification.data?.url);

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (windowClients) => {
            for (let client of windowClients) {
                if ('focus' in client) {
                    await client.navigate(urlAlvo);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlAlvo);
            }
        })
    );
});
