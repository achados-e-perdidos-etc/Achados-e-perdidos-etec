// A assinatura pertence à sessão, sem escolher destinatário por RM no navegador.
let cicloPush = 0;

async function ativarWebPush() {
    const token = SessaoPortal.token();
    if (!token || !('serviceWorker' in navigator) || !('PushManager' in window)
        || !('Notification' in window) || Notification.permission !== 'granted') return false;
    const ciclo = cicloPush;
    const sessaoAtiva = () => ciclo === cicloPush && SessaoPortal.token() === token;
    try {
        const existente = await navigator.serviceWorker.getRegistration();
        if (!sessaoAtiva()) return false;
        if (!existente) await navigator.serviceWorker.register('/sw.js');
        if (!sessaoAtiva()) return false;
        const reg = await navigator.serviceWorker.ready;
        if (!sessaoAtiva()) return false;
        let sub = await reg.pushManager.getSubscription();
        if (!sessaoAtiva()) return false;
        if (!sub) {
            const res = await fetch(API_URL + '/api/push/public-key');
            if (!res.ok || !sessaoAtiva()) return false;
            const data = await res.json();
            if (!data.success || !data.publicKey || !sessaoAtiva()) return false;
            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(data.publicKey)
            });
        }
        if (!sessaoAtiva()) {
            if (!SessaoPortal.token()) await sub.unsubscribe();
            return false;
        }
        return await enviarSubscricaoAoBackend(sub, token);
    } catch (error) {
        return false;
    }
}

async function enviarSubscricaoAoBackend(sub, token = SessaoPortal.token()) {
    if (!token || SessaoPortal.token() !== token) return false;
    try {
        const res = await fetch(API_URL + '/api/push/subscribe', {
            method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
            body: JSON.stringify({subscription: sub})
        });
        const data = await res.json();
        return res.ok && data.success === true;
    } catch (error) {
        return false;
    }
}

async function desativarWebPush(token) {
    cicloPush++; // Invalida tarefas iniciadas antes do logout.
    if (!('serviceWorker' in navigator)) return;
    try {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = reg && await reg.pushManager.getSubscription();
        if (!sub) return;
        const tarefas = [sub.unsubscribe()];
        if (token) tarefas.push(fetch(API_URL + '/api/push/subscribe', {
            method: 'DELETE', keepalive: true,
            headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
            body: JSON.stringify({endpoint: sub.endpoint})
        }));
        await Promise.allSettled(tarefas);
    } catch (error) {
        // Logout continua disponível quando o navegador ou a rede falham.
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from(rawData, char => char.charCodeAt(0));
}
