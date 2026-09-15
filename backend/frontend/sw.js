const CACHE_NAME = 'etec-achados-v1';

// Arquivos visuais básicos para carregar a tela rápido
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/style.css'
];

// INSTALAÇÃO: Salva o visual básico e expulsa a versão velha
self.addEventListener('install', (e) => {
    self.skipWaiting();
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
});

// ATIVAÇÃO: Limpa qualquer cache de versões antigas do app
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            );
        })
    );
});

// INTERCEPTAÇÃO: Onde a mágica acontece
self.addEventListener('fetch', (e) => {
    // REGRA DE OURO: Nunca cachear o banco de dados (rotas da API)
    if (e.request.url.includes('/api/')) {
        return; // Deixa a requisição passar reto para a internet
    }

    // Para o resto (imagens, css, html): Tenta a internet, se cair ou demorar, mostra o cache
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
