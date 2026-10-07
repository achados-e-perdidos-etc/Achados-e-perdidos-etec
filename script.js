const API_URL = "https://etec-achados.up.railway.app";
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let termoBusca = '';
let fotosAtuais = [];
let fotoIndiceAtual = 0;
let abaAtiva = 'catalogo';
let chatAberto = false;
let chatTimerPolling = null;
let ultimaQtdMensagens = 0;
let alunoSessao = null;
let fotosAlunoSelecionadas = [];

// ============================================================
// COMPRESSOR INTELIGENTE DE FOTOS NO NAVEGADOR (HTML5 CANVAS)
// ============================================================
function comprimirImagem(arquivo, maxDim = 1200, qualidade = 0.75) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                let w = img.width;
                let h = img.height;
                if (w > maxDim || h > maxDim) {
                    if (w > h) {
                        h = Math.round((h * maxDim) / w);
                        w = maxDim;
                    } else {
                        w = Math.round((w * maxDim) / h);
                        h = maxDim;
                    }
                }
                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);
                resolve(canvas.toDataURL('image/jpeg', qualidade));
            };
            img.onerror = reject;
            img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(arquivo);
    });
}

// ============================================================
// DETECÇÃO DE CONEXÃO (ONLINE / OFFLINE)
// ============================================================
window.addEventListener('offline', () => {
    const banner = document.getElementById('bannerStatusRede');
    if (banner) banner.classList.remove('hidden');
    mostrarToast("Você está sem internet. Exibindo dados em cache offline.", "info");
});

window.addEventListener('online', () => {
    const banner = document.getElementById('bannerStatusRede');
    if (banner) banner.classList.add('hidden');
    mostrarToast("Conexão restabelecida! Atualizando pertences...", "success");
    carregarItensDaAPI();
});

// SOM DE NOTIFICAÇÃO VIA WEB AUDIO API
function tocarSomNotificacao() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, ctx.currentTime);
        osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.35);
    } catch(e) {}
}

function solicitarPermissaoNotificacao() {
    if ("Notification" in window) {
        if (Notification.permission === "granted") {
            mostrarToast("As notificações já estão ativadas!", "success");
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") mostrarToast("Notificações ativadas com sucesso!", "success");
            });
        }
    } else {
        mostrarToast("Seu navegador não suporta notificações nativas.", "error");
    }
}

function dispararNotificacaoNativa(titulo, corpo) {
    if ("Notification" in window && Notification.permission === "granted") {
        const notificacao = new Notification(titulo, { body: corpo, icon: "logo.png" });
        notificacao.onclick = function() { window.focus(); this.close(); };
    }
}

function calcularDiasPassados(dataStr) {
    if (!dataStr) return 0;
    const partes = String(dataStr).trim().split(/[\/\-]/);
    if (partes.length === 3) {
        let dia, mes, ano;
        if (partes[0].length === 4) {
            ano = parseInt(partes[0], 10);
            mes = parseInt(partes[1], 10) - 1;
            dia = parseInt(partes[2], 10);
        } else {
            dia = parseInt(partes[0], 10);
            mes = parseInt(partes[1], 10) - 1;
            ano = parseInt(partes[2], 10);
            if (ano < 100) ano += 2000;
        }
        if (isNaN(dia) || isNaN(mes) || isNaN(ano)) return 0;
        const dataItem = new Date(ano, mes, dia);
        if (isNaN(dataItem.getTime())) return 0;
        const diffTempo = new Date().getTime() - dataItem.getTime();
        return Math.floor(diffTempo / (1000 * 60 * 60 * 24));
    }
    return 0;
}

const CORES_MATCH_ALUNO = ['preto', 'preta', 'azul', 'vermelho', 'vermelha', 'rosa', 'verde', 'amarelo', 'amarela', 'cinza', 'branco', 'branca', 'prata', 'dourado', 'marrom', 'roxo', 'roxa'];

function calcularSmartMatchAluno(relato, item) {
    let score = 0;
    let motivos = [];

    const catRelato = (relato.categoria || '').trim().toUpperCase();
    const catItem = (item.categoria || '').trim().toUpperCase();
    if (catRelato && catItem && catRelato === catItem) {
        score += 30;
        motivos.push(`Categoria ${catRelato}`);
    }

    const stopwords = new Set(['perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do', 'com', 'sem', 'favor', 'acho', 'que', 'objeto', 'achei']);
    function extrair(str) {
        return (str || '').toLowerCase().match(/[a-zA-Z0-9áéíóúãõâêîôûç]+/g) || [];
    }
    const termosRelato = extrair(relato.descricao).filter(p => p.length >= 3 && !stopwords.has(p));
    const termosItem = new Set(extrair(`${item.nome || ''} ${item.txt_descricao || ''}`).filter(p => p.length >= 3 && !stopwords.has(p)));
    
    const comuns = termosRelato.filter(t => termosItem.has(t));
    if (termosRelato.length > 0 && comuns.length > 0) {
        const pct = comuns.length / Math.max(1, termosRelato.length);
        score += Math.min(40, Math.round(pct * 40));
        motivos.push(`${comuns.slice(0, 2).join(', ')}`);
    }

    const coresRelato = extrair(relato.descricao).filter(p => CORES_MATCH_ALUNO.includes(p));
    const coresItem = new Set(extrair(`${item.nome || ''} ${item.txt_descricao || ''}`).filter(p => CORES_MATCH_ALUNO.includes(p)));
    const coresComuns = coresRelato.filter(c => coresItem.has(c));
    if (coresComuns.length > 0) {
        score += 15;
        motivos.push(`Cor ${coresComuns[0]}`);
    }

    return { score: Math.min(100, score), motivos };
}

function normalizarStatus(itemOuStatus, dataItem = null) {
    let st = '';
    let dataStr = dataItem;
    if (typeof itemOuStatus === 'object' && itemOuStatus !== null) {
        st = (itemOuStatus.status || 'DISPONÍVEL').toUpperCase().trim();
        dataStr = itemOuStatus.data_encontrado || itemOuStatus.txt_data;
    } else {
        st = (itemOuStatus || 'DISPONÍVEL').toUpperCase().trim();
    }

    if (st.includes('DOAÇÃO') || st.includes('DOACAO')) {
        return 'PARA DOAÇÃO';
    }
    if (st === 'ENTREGUE' || st === 'SOLICITADO') {
        return st;
    }

    if (st === 'DISPONÍVEL' && dataStr) {
        const dias = calcularDiasPassados(dataStr);
        if (dias >= 90) {
            return 'PARA DOAÇÃO';
        }
    }
    return st;
}

async function ativarWebPush(rm) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    try {
        const reg = await navigator.serviceWorker.register('/sw.js');
        let sub = await reg.pushManager.getSubscription();
        if (!sub) {
            const resKey = await fetch(`${API_URL}/api/push/vapid-key`);
            if (!resKey.ok) return;
            const { publicKey } = await resKey.json();
            if (!publicKey) return;
            
            const convertedKey = urlBase64ToUint8Array(publicKey);
            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedKey
            });
        }
        await fetch(`${API_URL}/api/push/inscrever`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rm, subscription: sub })
        });
    } catch (e) {}
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function checarSessao() {
    const token = localStorage.getItem('aluno_token');
    const dados = localStorage.getItem('aluno_dados');
    
    if (token && dados) {
        try {
            const res = await fetch(`${API_URL}/api/auth/verificar`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.status === 401) {
                fazerLogoff(false);
                mostrarToast("Sua sessão expirou. Faça login novamente.", "info");
                return;
            }
        } catch (e) {}

        alunoSessao = JSON.parse(dados);
        ativarWebPush(alunoSessao.rm);
        document.getElementById('loginAlunoScreen').classList.add('hidden');
        document.getElementById('lblBemVindo').innerText = `Olá, ${alunoSessao.nome.split(' ')[0]}!`;
        
        document.getElementById('perfilNomeCompleto').innerText = alunoSessao.nome;
        document.getElementById('perfilEmailInstitucional').innerText = alunoSessao.email;
        document.getElementById('perfilRM').innerText = (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor') ? 'PROFESSOR (Apenas Cadastro)' : (alunoSessao.rm || 'N/A');

        const ehProf = (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor');
        const bPerdi = document.getElementById('btnPerdiBanner');
        if (bPerdi) bPerdi.classList.toggle('hidden', ehProf);
        const mMural = document.getElementById('menuBtnMural');
        if (mMural) mMural.classList.toggle('hidden', ehProf);
        if (ehProf) {
            document.getElementById('lblBemVindo').innerText = "Olá, Professor(a)!";
        }

        carregarItensDaAPI();
        carregarCategoriasDinamicamente();
        
        if ("Notification" in window && Notification.permission === "default") {
            setTimeout(solicitarPermissaoNotificacao, 3000);
        }
    } else {
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
    }
}

function fazerLogoff(recarregar = true) {
    localStorage.removeItem('aluno_token');
    localStorage.removeItem('aluno_dados');
    if (recarregar) {
        window.location.reload();
    } else {
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
    }
}

function toggleMenuNavegacao() {
    const menu = document.getElementById('menuNavegacaoDropdown');
    const perfilMenu = document.getElementById('perfilMenu');
    const statusMenu = document.getElementById('dropdownStatusMenu');
    if(perfilMenu) perfilMenu.classList.add('hidden');
    if(statusMenu) statusMenu.classList.add('hidden');
    menu.classList.toggle('hidden');
}

function fecharMenuNavegacao() { 
    document.getElementById('menuNavegacaoDropdown').classList.add('hidden'); 
}

function togglePerfilMenu() {
    const menu = document.getElementById('perfilMenu');
    const navMenu = document.getElementById('menuNavegacaoDropdown');
    const statusMenu = document.getElementById('dropdownStatusMenu');
    if(navMenu) navMenu.classList.add('hidden');
    if(statusMenu) statusMenu.classList.add('hidden');
    menu.classList.toggle('hidden');
}

function togglePainelCategorias() {
    const painel = document.getElementById('categoryChipsContainer');
    const btn = document.getElementById('btnToggleFiltros');
    if (!painel) return;
    
    const estaOculto = painel.classList.contains('hidden');
    painel.classList.toggle('hidden');
    if (btn) {
        if (estaOculto) {
            btn.classList.add('border-red-500/80', 'text-red-400', 'bg-red-500/10');
        } else if (categoriaAtual === 'TODOS') {
            btn.classList.remove('border-red-500/80', 'text-red-400', 'bg-red-500/10');
        }
    }
}

function toggleDropdownStatus(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('dropdownStatusMenu');
    const seta = document.getElementById('setaStatusDropdown');
    const perfilMenu = document.getElementById('perfilMenu');
    const navMenu = document.getElementById('menuNavegacaoDropdown');
    if(navMenu) navMenu.classList.add('hidden');
    if(perfilMenu) perfilMenu.classList.add('hidden');
    
    const estaOculto = menu.classList.contains('hidden');
    menu.classList.toggle('hidden');
    if(seta) seta.classList.toggle('rotate-180', estaOculto);
}

function selecionarFiltroStatus(statusValor, statusLabel) {
    statusAtual = statusValor;
    document.getElementById('labelStatusSelecionado').innerText = statusLabel;
    document.getElementById('dropdownStatusMenu').classList.add('hidden');
    const seta = document.getElementById('setaStatusDropdown');
    if(seta) seta.classList.remove('rotate-180');
    renderizarItens();
}

window.addEventListener('click', (e) => {
    const navMenu = document.getElementById('menuNavegacaoDropdown');
    const navBtn = navMenu?.previousElementSibling;
    if (navMenu && !navMenu.contains(e.target) && !navBtn?.contains(e.target)) navMenu.classList.add('hidden');

    const perfilMenu = document.getElementById('perfilMenu');
    const perfilBtn = perfilMenu?.previousElementSibling;
    if (perfilMenu && !perfilMenu.contains(e.target) && !perfilBtn?.contains(e.target)) perfilMenu.classList.add('hidden');

    const statusMenu = document.getElementById('dropdownStatusMenu');
    const btnStatus = document.getElementById('btnDropdownStatus');
    if (statusMenu && !statusMenu.contains(e.target) && !btnStatus?.contains(e.target)) {
        statusMenu.classList.add('hidden');
        const seta = document.getElementById('setaStatusDropdown');
        if(seta) seta.classList.remove('rotate-180');
    }
});

function alternarTelaAuth(tela) {
    document.getElementById('formLoginAluno').classList.add('hidden');
    document.getElementById('formCadastroAluno').classList.add('hidden');
    document.getElementById('formRecuperarAluno').classList.add('hidden');
    if (tela === 'login') document.getElementById('formLoginAluno').classList.remove('hidden');
    if (tela === 'cadastro') document.getElementById('formCadastroAluno').classList.remove('hidden');
    if (tela === 'recuperar') document.getElementById('formRecuperarAluno').classList.remove('hidden');
}

async function fazerLoginAluno(e) {
    e.preventDefault();
    const emailVal = document.getElementById('loginEmailAluno').value.trim().toLowerCase();
    const senhaVal = document.getElementById('loginSenhaAluno').value.trim().toLowerCase();

    if (emailVal === 'professor' && senhaVal === 'professor') {
        const btn = document.getElementById('btnAcessoLogin');
        btn.innerText = "Entrando..."; btn.disabled = true;
        try {
            const res = await fetch(API_URL + "/api/auth/login-aluno", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: 'professor', senha: 'professor' })
            });
            const data = await res.json();
            if (data.success && data.token) {
                localStorage.setItem('aluno_token', data.token.trim());
                localStorage.setItem('aluno_dados', JSON.stringify(data.aluno));
                mostrarToast("Bem-vindo(a), Professor(a)!", "success");
                checarSessao();
            } else {
                const profDados = { nome: "Professor(a)", rm: "PROFESSOR", email: "professor@cps.sp.gov.br", role: "professor" };
                localStorage.setItem('aluno_token', 'token_prof_' + Date.now());
                localStorage.setItem('aluno_dados', JSON.stringify(profDados));
                mostrarToast("Bem-vindo(a), Professor(a)!", "success");
                checarSessao();
            }
        } catch {
            const profDados = { nome: "Professor(a)", rm: "PROFESSOR", email: "professor@cps.sp.gov.br", role: "professor" };
            localStorage.setItem('aluno_token', 'token_prof_' + Date.now());
            localStorage.setItem('aluno_dados', JSON.stringify(profDados));
            mostrarToast("Bem-vindo(a), Professor(a)!", "success");
            checarSessao();
        }
        btn.innerText = "Entrar no Portal"; btn.disabled = false;
        return;
    }

    const btn = document.getElementById('btnAcessoLogin');
    btn.innerText = "Entrando..."; btn.disabled = true;
    try {
        const res = await fetch(API_URL + "/api/auth/login-aluno", {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email: document.getElementById('loginEmailAluno').value.trim(), 
                senha: document.getElementById('loginSenhaAluno').value.trim() 
            })
        });
        const data = await res.json();
        if (data.success && data.token) {
            localStorage.setItem('aluno_token', data.token.trim());
            localStorage.setItem('aluno_dados', JSON.stringify(data.aluno));
            checarSessao();
        } else {
            mostrarToast(data.message || "Erro no login.", "error");
        }
    } catch { 
        mostrarToast("Erro ao conectar com o servidor.", "error"); 
    }
    btn.innerText = "Entrar no Portal"; btn.disabled = false;
}

async function enviarCodigoAuth(idEmail, idBtn, idShow, idHide) {
    const email = document.getElementById(idEmail).value.trim();
    if (!email.endsWith("@aluno.cps.sp.gov.br")) return mostrarToast("Use um e-mail @aluno.cps.sp.gov.br", "error");
    const btn = document.getElementById(idBtn);
    btn.innerText = "Enviando..."; btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/auth/enviar-codigo`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ email }) 
        });
        const data = await res.json();
        if (data.success) { 
            document.getElementById(idShow).classList.remove('hidden'); 
            document.getElementById(idHide).classList.add('hidden'); 
            mostrarToast("Código enviado para seu e-mail!", "success");
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro na rede ao enviar código.", "error"); }
    btn.innerText = "Enviar Código"; btn.disabled = false;
}

async function confirmarCadastro(e) {
    e.preventDefault();
    const payload = { 
        email: document.getElementById('cadEmailAluno').value.trim(), 
        codigo: document.getElementById('cadCodigo').value.trim(), 
        nome: document.getElementById('cadNome').value.trim(), 
        rm: document.getElementById('cadRM').value.trim(), 
        senha: document.getElementById('cadSenha').value.trim() 
    };
    try {
        const res = await fetch(`${API_URL}/api/auth/cadastrar`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });
        const data = await res.json();
        if (data.success && data.token) {
            localStorage.setItem('aluno_token', data.token.trim()); 
            localStorage.setItem('aluno_dados', JSON.stringify(data.aluno)); 
            mostrarToast("Conta criada com sucesso!", "success");
            checarSessao();
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro ao finalizar cadastro.", "error"); }
}

async function confirmarRedefinicao(e) {
    e.preventDefault();
    const payload = { 
        email: document.getElementById('recEmailAluno').value.trim(), 
        codigo: document.getElementById('recCodigo').value.trim(), 
        senha: document.getElementById('recSenha').value.trim() 
    };
    try {
        const res = await fetch(`${API_URL}/api/auth/redefinir`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });
        const data = await res.json();
        if (data.success) { 
            mostrarToast("Senha alterada com sucesso!", "success"); 
            alternarTelaAuth('login'); 
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro ao redefinir senha.", "error"); }
}

function mostrarToast(mensagem, tipo = 'info') {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    const corIcone = tipo === 'success' ? 'text-emerald-400' : (tipo === 'error' ? 'text-rose-400' : 'text-blue-400');
    const icone = tipo === 'success' ? 'fa-check-circle' : (tipo === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle');
    
    t.className = `glass-panel text-white px-4 py-3 rounded-2xl flex items-center gap-3 toast-enter pointer-events-auto shadow-2xl border border-white/10 min-w-[280px] max-w-sm`;
    t.innerHTML = `
        <i class="fas ${icone} ${corIcone} text-base shrink-0"></i>
        <p class="text-xs font-semibold flex-grow leading-snug">${mensagem}</p>
        <button onclick="this.parentElement.remove()" class="text-slate-500 hover:text-white text-xs"><i class="fas fa-times"></i></button>
    `;
    c.appendChild(t); 
    setTimeout(() => t.remove(), 4200);
}

function fecharZoomImagemDirect() { 
    document.getElementById('modalZoomImagem').classList.remove('ativo'); 
    document.body.style.overflow = ''; 
}
function fecharZoomImagem(e) { 
    if (e.target.id === 'modalZoomImagem') fecharZoomImagemDirect(); 
}
function abrirZoomImagem(src) { 
    document.getElementById('imgZoomConteudo').src = src; 
    document.getElementById('modalZoomImagem').classList.add('ativo'); 
    document.body.style.overflow = 'hidden'; 
}

function mudarAba(aba) {
    abaAtiva = aba;
    document.getElementById('catalogScreen').classList.toggle('hidden', aba !== 'catalogo');
    document.getElementById('muralScreen').classList.toggle('hidden', aba !== 'mural');
    document.getElementById('meusItensScreen').classList.toggle('hidden', aba !== 'meusItens');
    document.getElementById('detailScreen').classList.add('hidden');
    if (aba === 'mural') carregarMuralPublico();
}

async function abrirPainelMeusItens() {
    mudarAba('meusItens');
    if (!alunoSessao) return;

    const listaSol = document.getElementById('listaMinhasSolicitacoes');
    const listaRel = document.getElementById('listaMeusRelatosMural');
    
    listaSol.innerHTML = `<p class="text-xs text-slate-500 italic">Buscando solicitações...</p>`;
    listaRel.innerHTML = `<p class="text-xs text-slate-500 italic">Buscando relatos...</p>`;

    try {
        const resItens = await fetch(`${API_URL}/api/itens`);
        if (resItens.ok) {
            const itens = await resItens.json();
            const meus = itens.filter(i => i.rm_aluno === alunoSessao.rm || i.solicitado_por === alunoSessao.nome);
            
            if (meus.length > 0) {
                listaSol.innerHTML = '';
                meus.forEach(i => {
                    const st = normalizarStatus(i);
                    listaSol.innerHTML += `
                        <div class="glass-panel rounded-2xl p-4 flex justify-between items-center gap-3 border border-white/5">
                            <div>
                                <p class="text-xs font-bold text-white">${i.nome || i.txt_descricao}</p>
                                <p class="text-[10px] text-slate-400 mt-0.5">Status: <span class="font-bold text-amber-400 uppercase">${st}</span></p>
                            </div>
                            <button onclick='abrirDetalhes(${JSON.stringify(i).replace(/'/g, "&apos;")})' class="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-white transition">VER</button>
                        </div>`;
                });
            } else listaSol.innerHTML = `<p class="text-xs text-slate-500 italic">Você ainda não solicitou nenhum item.</p>`;
        }

        const resMural = await fetch(`${API_URL}/api/mural/aluno/${alunoSessao.rm}`);
        if (resMural.ok) {
            const relatos = await resMural.json();
            if (relatos.length > 0) {
                listaRel.innerHTML = '';
                relatos.forEach(r => {
                    const matches = [];
                    (todosItens || []).forEach(it => {
                        const st = normalizarStatus(it);
                        if (st === 'DISPONÍVEL') {
                            const res = calcularSmartMatchAluno(r, it);
                            if (res.score >= 50) matches.push({ item: it, score: res.score });
                        }
                    });
                    matches.sort((a, b) => b.score - a.score);

                    let htmlMatchBadge = '';
                    if (matches.length > 0) {
                        const top = matches[0];
                        htmlMatchBadge = `
                            <div class="mt-2.5 pt-2.5 border-t border-white/5 flex items-center justify-between">
                                <span class="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5">
                                    <i class="fas fa-magic"></i> Encontramos item compatível (${top.score}%)
                                </span>
                                <button onclick='abrirDetalhes(${JSON.stringify(top.item).replace(/'/g, "&apos;")})' class="px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-[11px] font-bold text-emerald-300 transition">
                                    Ver Objeto
                                </button>
                            </div>
                        `;
                    }

                    listaRel.innerHTML += `
                        <div class="glass-panel rounded-2xl p-4 border border-white/5">
                            <div class="flex justify-between items-center gap-3">
                                <div>
                                    <p class="text-xs font-bold text-white"><span class="text-amber-400">[${r.categoria}]</span> ${r.descricao}</p>
                                    <p class="text-[10px] text-slate-400 mt-0.5">Data do registro: ${r.data || 'Recente'}</p>
                                </div>
                                <span class="text-[10px] font-black px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wider shrink-0">ATIVO</span>
                            </div>
                            ${htmlMatchBadge}
                        </div>`;
                });
            } else listaRel.innerHTML = `<p class="text-xs text-slate-500 italic">Nenhum relato publicado no mural.</p>`;
        }
    } catch (e) {
        listaSol.innerHTML = `<p class="text-xs text-rose-400">Erro ao carregar solicitações.</p>`;
        listaRel.innerHTML = `<p class="text-xs text-rose-400">Erro ao carregar relatos.</p>`;
    }
}

function selecionarFiltroCategoria(catNome, catLabel) {
    categoriaAtual = catNome;
    document.querySelectorAll('.category-chip').forEach(btn => {
        btn.className = "category-chip px-3.5 py-1.5 rounded-xl text-xs font-bold border transition shrink-0 bg-white/5 text-slate-300 border-white/10 hover:bg-white/10";
    });
    const chipAtivo = document.getElementById(catNome === 'TODOS' ? 'chipCatTodos' : `chipCat_${catNome}`);
    if (chipAtivo) {
        chipAtivo.className = "category-chip px-3.5 py-1.5 rounded-xl text-xs font-bold border transition shrink-0 bg-red-600 text-white border-red-500 shadow-md";
    }

    const ind = document.getElementById('categoriaAtivaIndicador');
    if (ind) ind.innerText = catNome === 'TODOS' ? 'Todas' : catNome;

    const btnFiltro = document.getElementById('btnToggleFiltros');
    if (btnFiltro) {
        if (catNome !== 'TODOS') {
            btnFiltro.classList.add('border-red-500', 'text-red-400', 'bg-red-500/10');
        } else {
            btnFiltro.classList.remove('border-red-500', 'text-red-400', 'bg-red-500/10');
        }
    }

    renderizarItens();
}

async function carregarCategoriasDinamicamente() {
    try {
        const res = await fetch(`${API_URL}/api/categorias`);
        if (res.ok) {
            const cats = await res.json();
            const containerChips = document.getElementById('dynamicChipsList');
            const selectMural = document.getElementById('muralCategoria');
            const selectAlunoCad = document.getElementById('alunoItemCat');

            if (containerChips) {
                containerChips.innerHTML = '';
                cats.forEach(c => {
                    containerChips.innerHTML += `
                        <button id="chipCat_${c.nome}" onclick="selecionarFiltroCategoria('${c.nome}', '${c.nome}')" class="category-chip px-3.5 py-1.5 rounded-xl text-xs font-bold border transition shrink-0 bg-white/5 text-slate-300 border-white/10 hover:bg-white/10">
                            ${c.nome}
                        </button>`;
                });
            }
            if (selectMural) {
                selectMural.innerHTML = '';
                cats.forEach(c => { selectMural.innerHTML += `<option value="${c.nome}">${c.nome}</option>`; });
            }
            if (selectAlunoCad) {
                selectAlunoCad.innerHTML = '';
                cats.forEach(c => { selectAlunoCad.innerHTML += `<option value="${c.nome}">${c.nome}</option>`; });
            }
        }
    } catch (e) {}
}

async function carregarItensDaAPI() {
    const cacheSalvo = localStorage.getItem('cache_itens_etec');
    if (cacheSalvo) {
        try {
            todosItens = JSON.parse(cacheSalvo);
            renderizarItens();
        } catch(e) {}
    }

    try {
        const response = await fetch(`${API_URL}/api/itens`);
        if (response.ok) { 
            const data = await response.json();
            if (Array.isArray(data)) {
                todosItens = data;
                localStorage.setItem('cache_itens_etec', JSON.stringify(todosItens));
                renderizarItens(); 
            }
        }
    } catch(e){
        if (todosItens.length > 0) {
            mostrarToast("Exibindo itens salvos no dispositivo.", "info");
        }
    }
    setTimeout(() => {
        const loader = document.getElementById('loadingOverlay');
        if (loader) loader.classList.add('fade-out');
    }, 400);
}

function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    const contador = document.getElementById('itensContador');
    grid.innerHTML = '';
    
    const filtrados = todosItens.filter(i => {
        const st = normalizarStatus(i);
        return (categoriaAtual === 'TODOS' || (i.categoria && i.categoria.toUpperCase() === categoriaAtual)) &&
               (statusAtual === 'TODOS' || st === statusAtual) &&
               (!termoBusca || (i.nome||'').toLowerCase().includes(termoBusca) || (i.txt_descricao||'').toLowerCase().includes(termoBusca) || (i.txt_local||'').toLowerCase().includes(termoBusca));
    });

    if (contador) contador.innerText = `${filtrados.length} ${filtrados.length === 1 ? 'objeto encontrado' : 'objetos encontrados'}`;

    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full py-16 text-center glass-panel rounded-3xl border border-white/5 space-y-3">
                <i class="fas fa-search text-4xl text-slate-600"></i>
                <h4 class="text-sm font-bold text-white">Nenhum objeto localizado</h4>
                <p class="text-xs text-slate-400">Tente buscar por outros termos ou mudar o filtro de categoria.</p>
            </div>
        `;
        return;
    }

    filtrados.forEach(item => {
        const fotosArray = (item.fotos && item.fotos.length > 0) ? item.fotos : (item.foto ? [item.foto] : []);
        const imagemSrc = fotosArray[0] || '';
        const st = normalizarStatus(item);
        
        let badgeCor = 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
        if (st === 'SOLICITADO') {
            badgeCor = 'text-amber-400 border-amber-500/30 bg-amber-500/10';
        } else if (st === 'ENTREGUE') {
            badgeCor = 'text-slate-400 border-slate-700 bg-slate-800';
        } else if (st === 'PARA DOAÇÃO' || st.includes('DOAÇÃO') || st.includes('DOACAO')) {
            badgeCor = 'text-purple-400 border-purple-500/30 bg-purple-500/10';
        }

        grid.innerHTML += `
            <div onclick='abrirDetalhes(${JSON.stringify(item).replace(/'/g, "&apos;")})' class="interactive-card glass-panel rounded-3xl p-4 cursor-pointer flex flex-col justify-between group border border-white/10">
                <div>
                    <div class="relative w-full h-44 rounded-2xl overflow-hidden mb-3.5 bg-black/40 border border-white/5">
                        ${imagemSrc ? `<img src="${imagemSrc}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">` : `<div class="w-full h-full flex flex-col justify-center items-center text-slate-600"><i class="fas fa-box text-3xl mb-1"></i><span class="text-[10px] font-bold">Sem imagem</span></div>`}
                        <div class="absolute top-2.5 left-2.5">
                            <span class="text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-black/70 backdrop-blur-md text-white border border-white/10 shadow-sm">${item.categoria}</span>
                        </div>
                        <div class="absolute top-2.5 right-2.5">
                            <span class="text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider border shadow-sm ${badgeCor}">
                                ${st}
                            </span>
                        </div>
                        ${fotosArray.length > 1 ? `<div class="absolute bottom-2.5 right-2.5 bg-black/70 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded-md border border-white/10"><i class="fas fa-images mr-1"></i>${fotosArray.length}</div>` : ''}
                    </div>

                    <h4 class="font-extrabold text-sm text-white truncate tracking-tight">${item.nome || item.txt_descricao}</h4>
                    <p class="text-xs text-slate-400 line-clamp-2 mt-1 leading-snug">${item.txt_descricao}</p>
                </div>

                <div class="pt-3 mt-3 border-t border-white/5 flex justify-between items-center text-[11px] text-slate-400">
                    <span class="truncate max-w-[150px]"><i class="fas fa-map-marker-alt text-red-500 mr-1"></i>${item.txt_local}</span>
                    <span class="font-bold text-slate-300 flex items-center gap-1">Ver <i class="fas fa-chevron-right text-[9px] text-red-500"></i></span>
                </div>
            </div>
        `;
    });
}

function filtrarPorPalavraChave() { 
    termoBusca = document.getElementById('searchInput').value.toLowerCase().trim(); 
    document.getElementById('btnClearSearch').classList.toggle('hidden', !termoBusca);
    renderizarItens(); 
}

function limparBusca() { 
    document.getElementById('searchInput').value = ''; 
    termoBusca = ''; 
    document.getElementById('btnClearSearch').classList.add('hidden');
    renderizarItens(); 
}

function abrirDetalhes(item) {
    itemSelecionado = item;
    document.getElementById('catalogScreen').classList.add('hidden');
    document.getElementById('muralScreen').classList.add('hidden');
    document.getElementById('meusItensScreen').classList.add('hidden');
    document.getElementById('detailScreen').classList.remove('hidden');

    document.getElementById('detailTitle').innerText = item.nome || item.txt_descricao;
    document.getElementById('detailDescription').innerText = item.txt_descricao;
    document.getElementById('detailLocal').innerText = item.txt_local;
    document.getElementById('detailDate').innerText = item.txt_data;
    document.getElementById('detailCategoryBadge').innerText = item.categoria;

    const st = normalizarStatus(item);
    const badgeEl = document.getElementById('detailStatusBadge');
    badgeEl.innerText = st;
    if (st === 'DISPONÍVEL') badgeEl.className = "text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
    else if (st === 'SOLICITADO') badgeEl.className = "text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/30";
    else if (st === 'PARA DOAÇÃO') badgeEl.className = "text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-purple-500/15 text-purple-400 border border-purple-500/30";
    else badgeEl.className = "text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-slate-800 text-slate-400 border border-slate-700";

    const cont = document.getElementById('carouselContainer');
    cont.innerHTML = ''; 
    fotosAtuais = (item.fotos && item.fotos.length > 0) ? item.fotos : (item.foto ? [item.foto] : []);
    
    const counterEl = document.getElementById('photoCounter');
    const btnPrev = document.getElementById('btnPrevPhoto');
    const btnNext = document.getElementById('btnNextPhoto');

    if(fotosAtuais.length > 0) {
        document.getElementById('detailPlaceholder').classList.add('hidden');
        fotosAtuais.forEach(f => {
            cont.innerHTML += `<div class="w-full h-full flex-shrink-0 snap-center flex justify-center items-center p-2"><img src="${f}" onclick="abrirZoomImagem('${f}')" class="max-h-full max-w-full object-contain rounded-xl cursor-zoom-in"></div>`;
        });
        if (fotosAtuais.length > 1) {
            counterEl.classList.remove('hidden');
            btnPrev.classList.remove('hidden');
            btnNext.classList.remove('hidden');
            document.getElementById('photoCurrentIdx').innerText = "1";
            document.getElementById('photoTotalCount').innerText = fotosAtuais.length;
        } else {
            counterEl.classList.add('hidden');
            btnPrev.classList.add('hidden');
            btnNext.classList.add('hidden');
        }
    } else {
        document.getElementById('detailPlaceholder').classList.remove('hidden');
        counterEl.classList.add('hidden');
        btnPrev.classList.add('hidden');
        btnNext.classList.add('hidden');
    }
    
    const b = document.getElementById('btnSolicitar');
    const ehProf = alunoSessao && (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor');
    if (ehProf) {
        b.disabled = true;
        b.innerText = "PROFESSORES NÃO PODEM SOLICITAR ITENS";
        b.className = "w-full bg-slate-800 text-slate-400 font-bold py-3.5 rounded-xl text-xs uppercase cursor-not-allowed border border-white/5 opacity-80";
    } else if (st !== 'DISPONÍVEL') { 
        b.disabled = true; 
        b.innerText = `STATUS: ${st}`; 
        b.className = "w-full bg-slate-800 text-slate-500 font-bold py-3.5 rounded-xl text-xs uppercase cursor-not-allowed"; 
    } else { 
        b.disabled = false; 
        b.innerText = "ESTE É O MEU ITEM"; 
        b.className = "w-full bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-extrabold py-3.5 rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-red-600/30 transition transform active:scale-[0.98]"; 
    }
}

function navegarFotos(dir) {
    const cont = document.getElementById('carouselContainer');
    if (!cont || fotosAtuais.length <= 1) return;
    fotoIndiceAtual += dir;
    if (fotoIndiceAtual < 0) fotoIndiceAtual = fotosAtuais.length - 1;
    if (fotoIndiceAtual >= fotosAtuais.length) fotoIndiceAtual = 0;
    
    const w = cont.clientWidth;
    cont.scrollTo({ left: w * fotoIndiceAtual, behavior: 'smooth' });
    document.getElementById('photoCurrentIdx').innerText = fotoIndiceAtual + 1;
}

function voltarParaCatalogo() {
    document.getElementById('detailScreen').classList.add('hidden');
    document.getElementById('catalogScreen').classList.remove('hidden');
}

function abrirNovoModal() {
    if (!alunoSessao) return mostrarToast("Faça login para continuar.", "error");
    if (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor') {
        return mostrarToast("Professores não podem solicitar a retirada de pertences.", "info");
    }
    document.getElementById('modalNovo').classList.remove('hidden');
}

async function enviarNovo() {
    if (!itemSelecionado || !alunoSessao) return;
    const b = document.getElementById('btnNovo');
    b.innerText = "Enviando..."; b.disabled = true;

    try {
        const res = await fetch(`${API_URL}/api/solicitar-item`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_item: itemSelecionado.id,
                aluno_nome: alunoSessao.nome,
                aluno_rm: alunoSessao.rm,
                aluno_email: alunoSessao.email
            })
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast("Solicitação enviada com sucesso! Dirija-se à secretaria.", "success");
            document.getElementById('modalNovo').classList.add('hidden');
            carregarItensDaAPI();
            voltarParaCatalogo();
        } else {
            mostrarToast(data.message || "Erro ao solicitar item.", "error");
        }
    } catch (e) {
        mostrarToast("Erro de comunicação com o servidor.", "error");
    }
    b.innerText = "Sim, é meu!"; b.disabled = false;
}

async function enviarAvisoMural(e) {
    e.preventDefault();
    if (!alunoSessao) return mostrarToast("Faça login para relatar.", "error");
    
    const cat = document.getElementById('muralCategoria').value;
    const desc = document.getElementById('muralDescricao').value.trim();
    if (!desc) return mostrarToast("Informe a descrição do objeto.", "error");

    const b = document.getElementById('btnPublicarMural');
    b.innerText = "Publicando..."; b.disabled = true;

    try {
        const res = await fetch(`${API_URL}/api/mural`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rm: alunoSessao.rm,
                aluno_nome: alunoSessao.nome,
                categoria: cat,
                descricao: desc
            })
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast("Relato publicado no mural!", "success");
            document.getElementById('muralDescricao').value = '';
            carregarMuralPublico();

            // VERIFICA MATCH IMEDIATO NO CATÁLOGO
            const relatoFicticio = { categoria: cat, descricao: desc };
            const matches = [];
            (todosItens || []).forEach(it => {
                if (normalizarStatus(it) === 'DISPONÍVEL') {
                    const m = calcularSmartMatchAluno(relatoFicticio, it);
                    if (m.score >= 50) matches.push({ item: it, score: m.score, motivos: m.motivos });
                }
            });

            if (matches.length > 0) {
                matches.sort((x, y) => y.score - x.score);
                const listaEl = document.getElementById('matchItensLista');
                listaEl.innerHTML = '';
                matches.slice(0, 3).forEach(m => {
                    const fotosArray = (m.item.fotos && m.item.fotos.length > 0) ? m.item.fotos : (m.item.foto ? [m.item.foto] : []);
                    listaEl.innerHTML += `
                        <div class="glass-panel p-3 rounded-2xl flex items-center justify-between gap-3 border border-emerald-500/30 bg-emerald-500/5">
                            <div class="flex items-center gap-3">
                                ${fotosArray[0] ? `<img src="${fotosArray[0]}" class="w-12 h-12 object-cover rounded-xl border border-white/10">` : `<div class="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-slate-500"><i class="fas fa-box"></i></div>`}
                                <div>
                                    <p class="text-xs font-bold text-white">${m.item.nome || m.item.txt_descricao}</p>
                                    <span class="text-[10px] text-emerald-400 font-bold">${m.score}% de compatibilidade (${m.motivos.join(', ')})</span>
                                </div>
                            </div>
                            <button onclick="document.getElementById('modalMatchImediato').classList.add('hidden'); abrirDetalhes(${JSON.stringify(m.item).replace(/'/g, "&apos;")});" class="px-3 py-1.5 rounded-xl bg-emerald-600 text-white font-bold text-xs shadow-md hover:bg-emerald-500 transition">Ver</button>
                        </div>
                    `;
                });
                document.getElementById('modalMatchImediato').classList.remove('hidden');
            }
        } else {
            mostrarToast(data.message || "Erro ao publicar relato.", "error");
        }
    } catch (e) {
        mostrarToast("Erro de comunicação ao publicar relato.", "error");
    }
    b.innerText = "Publicar Relato no Mural"; b.disabled = false;
}

async function carregarMuralPublico() {
    const c = document.getElementById('listaMuralPublico');
    c.innerHTML = '<p class="text-xs text-slate-500 italic">Carregando relatos...</p>';
    try {
        const res = await fetch(`${API_URL}/api/mural/publico`);
        if (res.ok) {
            const relatos = await res.json();
            if (relatos.length === 0) {
                c.innerHTML = '<p class="text-xs text-slate-500 italic">Nenhum relato no mural até o momento.</p>';
                return;
            }
            c.innerHTML = '';
            relatos.forEach(r => {
                c.innerHTML += `
                    <div class="glass-panel rounded-2xl p-4 space-y-1.5 border border-white/5">
                        <div class="flex justify-between items-center text-[10px] font-bold text-slate-400">
                            <span class="text-amber-400 font-extrabold uppercase">[${r.categoria}]</span>
                            <span>${r.data || 'Recente'}</span>
                        </div>
                        <p class="text-xs font-semibold text-slate-200 leading-relaxed">${r.descricao}</p>
                        <p class="text-[10px] text-slate-500 text-right font-medium">— Por: ${r.aluno_nome || 'Aluno'}</p>
                    </div>
                `;
            });
        }
    } catch (e) {
        c.innerHTML = '<p class="text-xs text-rose-400">Erro ao atualizar mural.</p>';
    }
}

function abrirModalCadastrarAluno() {
    if (!alunoSessao) return mostrarToast("Faça login para cadastrar um objeto.", "error");
    fotosAlunoSelecionadas = [];
    document.getElementById('gridPreviewAluno').innerHTML = '';
    document.getElementById('gridPreviewAluno').classList.add('hidden');
    document.getElementById('btnAutoPreencherIAAluno').classList.add('hidden');
    document.getElementById('statusCompressaoFotos').classList.add('hidden');
    document.getElementById('modalCadastrarAluno').classList.remove('hidden');
}

async function prepararFotosAluno(input) {
    const files = Array.from(input.files).slice(0, 4);
    if (files.length === 0) return;

    fotosAlunoSelecionadas = [];
    const grid = document.getElementById('gridPreviewAluno');
    grid.innerHTML = '<span class="text-[10px] text-slate-400 animate-pulse">Otimizando imagens...</span>';
    grid.classList.remove('hidden');

    for (let f of files) {
        try {
            const base64Comprimido = await comprimirImagem(f, 1000, 0.7);
            fotosAlunoSelecionadas.push(base64Comprimido);
        } catch (e) {}
    }

    grid.innerHTML = '';
    fotosAlunoSelecionadas.forEach((src, idx) => {
        grid.innerHTML += `
            <div class="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 border border-white/10 group">
                <img src="${src}" class="w-full h-full object-cover">
                <button type="button" onclick="removerFotoAluno(${idx})" class="absolute top-1 right-1 bg-black/80 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"><i class="fas fa-times"></i></button>
            </div>
        `;
    });

    if (fotosAlunoSelecionadas.length > 0) {
        document.getElementById('statusCompressaoFotos').classList.remove('hidden');
        document.getElementById('btnAutoPreencherIAAluno').classList.remove('hidden');
    }
}

function removerFotoAluno(idx) {
    fotosAlunoSelecionadas.splice(idx, 1);
    const grid = document.getElementById('gridPreviewAluno');
    grid.innerHTML = '';
    fotosAlunoSelecionadas.forEach((src, i) => {
        grid.innerHTML += `
            <div class="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 border border-white/10 group">
                <img src="${src}" class="w-full h-full object-cover">
                <button type="button" onclick="removerFotoAluno(${i})" class="absolute top-1 right-1 bg-black/80 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition"><i class="fas fa-times"></i></button>
            </div>
        `;
    });
    if (fotosAlunoSelecionadas.length === 0) {
        grid.classList.add('hidden');
        document.getElementById('btnAutoPreencherIAAluno').classList.add('hidden');
        document.getElementById('statusCompressaoFotos').classList.add('hidden');
    }
}

async function analisarFotoAlunoComIA() {
    if (fotosAlunoSelecionadas.length === 0) return mostrarToast("Selecione pelo menos uma foto.", "error");

    const btn = document.getElementById('btnAutoPreencherIAAluno');
    const txtOriginal = btn.innerHTML;
    btn.innerHTML = `<i class="fas fa-circle-notch animate-spin"></i> Analisando imagem com IA...`;
    btn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/api/analisar-imagem-ia`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ imagem_base64: fotosAlunoSelecionadas[0] })
        });
        const data = await res.json();
        if (data.success && data.analise) {
            const a = data.analise;
            if (a.nome) document.getElementById('alunoItemNome').value = a.nome;
            if (a.descricao) document.getElementById('alunoItemDesc').value = a.descricao;
            if (a.categoria) {
                const sel = document.getElementById('alunoItemCat');
                for (let opt of sel.options) {
                    if (opt.value.toUpperCase() === a.categoria.toUpperCase()) {
                        sel.value = opt.value;
                        break;
                    }
                }
            }
            mostrarToast("Campos preenchidos automaticamente pela IA!", "success");
        } else {
            mostrarToast(data.message || "Não foi possível analisar a imagem.", "error");
        }
    } catch (e) {
        mostrarToast("Erro ao conectar com a API de IA.", "error");
    }
    btn.innerHTML = txtOriginal;
    btn.disabled = false;
}

async function enviarCadastroAluno(e) {
    e.preventDefault();
    if (!alunoSessao) return mostrarToast("Sua sessão expirou.", "error");

    const nome = document.getElementById('alunoItemNome').value.trim();
    const desc = document.getElementById('alunoItemDesc').value.trim();
    const cat = document.getElementById('alunoItemCat').value;
    const local = document.getElementById('alunoItemLocal').value.trim();

    if (!nome || !desc || !local) return mostrarToast("Preencha todos os campos obrigatórios.", "error");

    const btn = document.getElementById('btnSalvarAlunoItem');
    btn.innerText = "Cadastrando..."; btn.disabled = true;

    try {
        const res = await fetch(`${API_URL}/api/cadastrar-item-aluno`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome: nome,
                descricao: desc,
                categoria: cat,
                local: local,
                fotos: fotosAlunoSelecionadas,
                cadastrado_por_nome: alunoSessao.nome,
                cadastrado_por_rm: alunoSessao.rm,
                cadastrado_por_email: alunoSessao.email
            })
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast("Item cadastrado! Entregue-o na secretaria para aprovação.", "success");
            document.getElementById('modalCadastrarAluno').classList.add('hidden');
            document.getElementById('alunoItemNome').value = '';
            document.getElementById('alunoItemDesc').value = '';
            document.getElementById('alunoItemLocal').value = '';
            fotosAlunoSelecionadas = [];
        } else {
            mostrarToast(data.message || "Erro ao cadastrar item.", "error");
        }
    } catch (e) {
        mostrarToast("Erro ao enviar cadastro.", "error");
    }
    btn.innerText = "Enviar para Moderação da Secretaria"; btn.disabled = false;
}

// ============================================================
// CHAT INTERATIVO COM A SECRETARIA
// ============================================================
function alternarJanelaChat() {
    chatAberto = !chatAberto;
    const janela = document.getElementById('janelaChat');
    janela.classList.toggle('hidden', !chatAberto);
    
    if (chatAberto) {
        carregarMensagensChat();
        if (!chatTimerPolling) chatTimerPolling = setInterval(carregarMensagensChat, 4000);
    } else {
        if (chatTimerPolling) {
            clearInterval(chatTimerPolling);
            chatTimerPolling = null;
        }
    }
}

function abrirChatComItem() {
    if (!chatAberto) alternarJanelaChat();
    if (itemSelecionado) {
        const input = document.getElementById('chatInputTexto');
        input.value = `Olá! Tenho dúvidas sobre o item #${itemSelecionado.id} (${itemSelecionado.nome || itemSelecionado.txt_descricao}).`;
        input.focus();
    }
}

async function carregarMensagensChat() {
    if (!alunoSessao || !alunoSessao.rm) return;
    try {
        const res = await fetch(`${API_URL}/api/chat/mensagens/${alunoSessao.rm}`);
        if (res.ok) {
            const msgs = await res.json();
            const cont = document.getElementById('chatMensagens');
            
            if (msgs.length > ultimaQtdMensagens && ultimaQtdMensagens !== 0) {
                tocarSomNotificacao();
            }
            ultimaQtdMensagens = msgs.length;

            if (msgs.length === 0) {
                cont.innerHTML = `
                    <div class="text-center py-8 space-y-2">
                        <i class="fas fa-comments text-slate-600 text-3xl"></i>
                        <p class="text-xs text-slate-400 font-medium">Inicie uma conversa diretamente com a secretaria para tirar dúvidas sobre objetos.</p>
                    </div>
                `;
                return;
            }

            cont.innerHTML = '';
            msgs.forEach(m => {
                const ehAluno = m.remetente === 'aluno' || m.rm_aluno === alunoSessao.rm;
                cont.innerHTML += `
                    <div class="flex flex-col ${ehAluno ? 'items-end' : 'items-start'}">
                        <div class="max-w-[82%] px-3.5 py-2.5 rounded-2xl text-xs ${ehAluno ? 'bg-red-600 text-white rounded-br-none' : 'bg-[#1a2233] text-slate-200 border border-white/10 rounded-bl-none'}">
                            <p class="leading-relaxed font-medium">${m.texto}</p>
                        </div>
                        <span class="text-[9px] text-slate-500 mt-1 px-1">${m.hora || 'Agora'}</span>
                    </div>
                `;
            });
            cont.scrollTop = cont.scrollHeight;
        }
    } catch (e) {}
}

async function enviarMensagemChat(e) {
    e.preventDefault();
    if (!alunoSessao) return mostrarToast("Faça login para enviar mensagens.", "error");

    const input = document.getElementById('chatInputTexto');
    const texto = input.value.trim();
    if (!texto) return;

    input.value = '';
    try {
        const res = await fetch(`${API_URL}/api/chat/enviar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rm_aluno: alunoSessao.rm,
                aluno_nome: alunoSessao.nome,
                remetente: 'aluno',
                texto: texto
            })
        });
        if (res.ok) {
            carregarMensagensChat();
        } else {
            mostrarToast("Erro ao enviar mensagem.", "error");
        }
    } catch (e) {
        mostrarToast("Erro de rede ao enviar mensagem.", "error");
    }
}

function atualizarPortalAluno() {
    const icone = document.getElementById('iconeRefreshPortal');
    if (icone) icone.classList.add('animate-spin');
    
    carregarItensDaAPI();
    carregarCategoriasDinamicamente();
    
    setTimeout(() => {
        if (icone) icone.classList.remove('animate-spin');
        mostrarToast("Portal atualizado com sucesso!", "success");
    }, 600);
}

// ============================================================
// INICIALIZAÇÃO DO APLICATIVO
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Tratamento e encerramento da Splash Screen (Vídeo / Timeout)
    const splash = document.getElementById('splashScreenAnimacao');
    const video = document.getElementById('videoSplash');

    if (splash) {
        const finalizarSplash = () => {
            splash.style.opacity = '0';
            setTimeout(() => splash.remove(), 700);
        };

        if (video) {
            video.onended = finalizarSplash;
            video.onerror = finalizarSplash;
            // Timeout de segurança caso o vídeo falhe ao carregar
            setTimeout(finalizarSplash, 4000);
        } else {
            finalizarSplash();
        }
    }

    // Inicializa a verificação de sessão e leitura da API
    checarSessao();
});
