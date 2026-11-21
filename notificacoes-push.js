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
        const chaveRes = await fetch(API_URL + '/api/push/public-key');
        if (!chaveRes.ok || !sessaoAtiva()) return false;
        const chaveData = await chaveRes.json();
        if (!chaveData.success || !chaveData.publicKey || !sessaoAtiva()) return false;
        const chaveAtual = urlBase64ToUint8Array(chaveData.publicKey);
        let sub = await reg.pushManager.getSubscription();
        if (sub?.options?.applicationServerKey) {
            const antiga = new Uint8Array(sub.options.applicationServerKey);
            if (antiga.length !== chaveAtual.length || antiga.some((v,i)=>v !== chaveAtual[i])) {
                await sub.unsubscribe(); sub = null;
            }
        }
        if (!sessaoAtiva()) return false;
        if (!sub) {
            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: chaveAtual
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


async function testarNotificacaoPush() {
    const btn = document.getElementById('btnTestarPush');
    if (btn.disabled) return;
    btn.disabled = true;
    try {
        if (!('Notification' in window)) throw Error('Este navegador não oferece notificações.');
        if (Notification.permission === 'default') await Notification.requestPermission();
        if (Notification.permission !== 'granted') throw Error('Permita notificações nas configurações do navegador.');
        if (!await ativarWebPush()) throw Error('Não foi possível ativar as notificações neste dispositivo.');
        const res = await fetch(API_URL + '/api/push/test', {
            method: 'POST', headers: {Authorization: `Bearer ${SessaoPortal.token()}`}
        });
        const data = await res.json();
        if (!res.ok || !data.success || !data.queued) throw Error(data.message || 'Não foi possível solicitar o teste.');
        mostrarToast('Teste solicitado. Aguarde a notificação.', 'info');
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível solicitar o teste.', 'info');
    } finally { btn.disabled = false; }
}
