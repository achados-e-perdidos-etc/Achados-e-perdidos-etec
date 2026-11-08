// ==============================================================================
// SERVICE WORKER - ETEC ACHADOS E PERDIDOS (VERSÃO 2.0 PWA & WEB PUSH)
// ==============================================================================

const CACHE_NAME = 'etec-achados-v28-abertura-leve';

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
    '/evolucao-interface.js',
    '/evolucao-interface.css',
    '/fila-offline.js',
    '/catalogo-portal.js',
    '/moderacao-interface.js',
    '/catalogo-moderacao.css',
    '/experiencia.js',
    '/abertura.js',
    '/experiencia.css',
    '/preferencias.css',
    '/tema.js',
    '/preferencias.js',
    '/vendor/tailwind.css',
    '/vendor/fontes.css',
    '/vendor/jakarta-0.woff2',
    '/vendor/inter-0.woff2',
    '/vendor/fontawesome/css/all.min.css',
    '/vendor/fontawesome/webfonts/fa-solid-900.woff2',
    '/vendor/fontawesome/webfonts/fa-regular-400.woff2',
    '/vendor/fontawesome/webfonts/fa-brands-400.woff2',
    '/vendor/fontawesome/webfonts/fa-v4compatibility.woff2',
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
    e.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(STATIC_ASSETS)).then(()=>self.skipWaiting()));
});

// ATIVAÇÃO: Invalida caches obsoletos
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((k) => k.startsWith('etec-achados-') && k !== CACHE_NAME).map((k) => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

// Somente a interface pública vai ao cache. APIs e requisições autenticadas seguem à rede.
self.addEventListener('fetch', event => {
    const url=new URL(event.request.url);
    if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/')
       ||event.request.headers.has('Authorization')||event.request.headers.has('x-access-token'))return;
    const conhecido=STATIC_ASSETS.includes(url.pathname);
    if(!conhecido&&event.request.mode!=='navigate')return;
    event.respondWith((async()=>{
        if(conhecido){const cached=await caches.match(event.request,{ignoreSearch:true});if(cached)return cached;}
        try{
            const response=await fetch(event.request);
            if(conhecido&&response.ok){const cache=await caches.open(CACHE_NAME);await cache.put(event.request,response.clone());}
            return response;
        }catch(_){
            const cached=await caches.match(event.request);if(cached)return cached;
            if(event.request.mode==='navigate')return await caches.match('/404.html')||Response.error();
            return Response.error();
        }
    })());
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
