const API_URL = "";
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let tempoAtual = 'TODOS';
let termoBusca = '';
let fotosAtuais = [];
let fotoIndiceAtual = 0;

let limiteItensExibidos = 12;

let apresentacaoItens = [];
let apresentacaoIndice = 0;
let apresentacaoTimer = null;
let modoApresentacaoAtivo = false;

let abaAtiva = 'catalogo';
let chatAberto = false;
let chatTimerPolling = null;
let ultimaQtdMensagens = 0;

async function carregarCategoriasDinamicamente() {
    try {
        const res = await fetch(`${API_URL}/api/categorias`);
        if (res.ok) {
            const cats = await res.json();
            const container = document.getElementById('categoryContainer');
            container.innerHTML = `<div id="catIndicator" class="sliding-pill absolute rounded-full z-0 opacity-0"></div>
                <button onclick="filtrarCategoria('TODOS', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-white border border-transparent transition-colors duration-200">TODOS</button>`;
            const selectMural = document.getElementById('muralCategoria');
            if (selectMural) selectMural.innerHTML = '';
            cats.forEach(c => {
                const btn = document.createElement('button');
                btn.onclick = function() { filtrarCategoria(c.nome, this) };
                btn.className = "cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-muted hover:text-main border border-color bg-card transition-colors duration-200";
                btn.innerText = c.nome;
                container.appendChild(btn);
                if (selectMural) {
                    const opt = document.createElement('option');
                    opt.value = c.nome; opt.innerText = c.nome;
                    selectMural.appendChild(opt);
                }
            });
        }
    } catch (e) { console.error("Erro categorias", e); }
}

function mudarAba(aba) {
    abaAtiva = aba;
    pararTemporizadorApresentacao();
    const catScreen = document.getElementById('catalogScreen');
    const muralScreen = document.getElementById('muralScreen');
    const apScreen = document.getElementById('apresentacaoScreen');
    const detScreen = document.getElementById('detailScreen');
    const btnCat = document.getElementById('tabBtnCatalogo');
    const btnMural = document.getElementById('tabBtnMural');

    apScreen.classList.add('hidden');
    detScreen.classList.add('hidden');

    if (aba === 'catalogo') {
        catScreen.classList.remove('hidden'); muralScreen.classList.add('hidden');
        btnCat.className = "px-3 py-2 rounded-lg bg-header border border-red-500 text-xs font-bold text-main transition flex items-center gap-1.5";
        btnMural.className = "relative px-3 py-2 rounded-lg bg-card border border-color text-xs font-bold text-muted hover:text-main transition flex items-center gap-1.5";
    } else {
        catScreen.classList.add('hidden'); muralScreen.classList.remove('hidden');
        btnMural.className = "relative px-3 py-2 rounded-lg bg-header border border-amber-500 text-xs font-bold text-main transition flex items-center gap-1.5";
        btnCat.className = "px-3 py-2 rounded-lg bg-card border border-color text-xs font-bold text-muted hover:text-main transition flex items-center gap-1.5";
        carregarFeedMural();
    }
}

function toggleConfigMenu() {
    const menu = document.getElementById('configMenu');
    if (menu) menu.classList.toggle('hidden');
}

window.addEventListener('click', function(e) {
    const menu = document.getElementById('configMenu');
    if (!menu) return;
    const btn = e.target.closest('button');
    if (!menu.contains(e.target) && (!btn || !btn.getAttribute('onclick')?.includes('toggleConfigMenu'))) {
        menu.classList.add('hidden');
    }
});

function aplicarTemaVermelho() {
    const root = document.documentElement;
    root.style.setProperty('--primary-color', '#dc2626');
    root.style.setProperty('--primary-hover', '#b91c1c');
    root.style.setProperty('--primary-text', '#f87171');
    root.style.setProperty('--primary-bg-subtle', '#450a0a');
    root.style.setProperty('--primary-border', '#991b1b');
}

function alternarModoEscuroClaro() {
    const isLight = document.body.classList.contains('light-theme');
    if (isLight) {
        document.body.classList.remove('light-theme'); document.body.classList.add('dark-theme'); localStorage.setItem('theme_mode', 'dark');
    } else {
        document.body.classList.remove('dark-theme'); document.body.classList.add('light-theme'); localStorage.setItem('theme_mode', 'light');
    }
}

function carregarPreferenciasAparencia() {
    aplicarTemaVermelho();
    if ((localStorage.getItem('theme_mode') || 'dark') === 'light') {
        document.body.classList.remove('dark-theme'); document.body.classList.add('light-theme');
    }
}

async function carregarItensDaAPI() {
    try {
        const response = await fetch(`${API_URL}/api/itens`);
        if (response.ok) {
            todosItens = await response.json();
            renderizarItens();
            atualizarItensApresentacao();
            verificarNotificacoesAutomaticas();
        }
    } catch (error) { console.error("Erro API:", error); }
}

function filtrarPorPalavraChave() {
    const btnClear = document.getElementById('btnClearSearch');
    termoBusca = document.getElementById('searchInput').value.trim().toLowerCase();
    if (btnClear) btnClear.classList.toggle('hidden', termoBusca.length === 0);
    limiteItensExibidos = 12; renderizarItens();
}

function limparBusca() {
    document.getElementById('searchInput').value = '';
    termoBusca = ''; document.getElementById('btnClearSearch')?.classList.add('hidden');
    limiteItensExibidos = 12; renderizarItens();
}

function filtrarStatus(status) { statusAtual = status; limiteItensExibidos = 12; renderizarItens(); }
function filtrarTempo(tempo) { tempoAtual = tempo; limiteItensExibidos = 12; renderizarItens(); }

function moveIndicator(element) {
    const indicator = document.getElementById('catIndicator');
    if (!indicator || !element) return;
    indicator.style.left = `${element.offsetLeft}px`;
    indicator.style.top = `${element.offsetTop}px`;
    indicator.style.width = `${element.offsetWidth}px`;
    indicator.style.height = `${element.offsetHeight}px`;
    indicator.classList.remove('opacity-0');
}

function filtrarCategoria(cat, btnElement) {
    categoriaAtual = cat;
    if (btnElement) {
        document.querySelectorAll('.cat-btn').forEach(b => {
            b.classList.remove('text-white', 'border-transparent'); b.classList.add('text-muted', 'border-color', 'bg-card');
        });
        btnElement.classList.remove('text-muted', 'border-color', 'bg-card'); btnElement.classList.add('text-white', 'border-transparent');
        moveIndicator(btnElement);
    }
    limiteItensExibidos = 12; renderizarItens();
}

function normalizarStatus(st) { return (st || 'DISPONÍVEL').toUpperCase() === 'GUARDADO' ? 'DISPONÍVEL' : (st || 'DISPONÍVEL').toUpperCase(); }

function parseDateBR(dateStr) {
    if(!dateStr) return new Date();
    const parts = dateStr.split(' ')[0].split('/'); 
    if(parts.length >= 3) return new Date(parts[2], parts[1] - 1, parts[0]);
    return new Date();
}

function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    const btnMais = document.getElementById('btnCarregarMais');
    if (!grid) return;
    grid.innerHTML = '';

    const today = new Date();
    today.setHours(0,0,0,0);

    const filtrados = todosItens.filter(item => {
        const cat = categoriaAtual === 'TODOS' || (item.categoria && item.categoria.toUpperCase() === categoriaAtual);
        const st = statusAtual === 'TODOS' || normalizarStatus(item.status) === normalizarStatus(statusAtual);
        
        let atendeTempo = true;
        if(tempoAtual !== 'TODOS') {
            const itemDate = parseDateBR(item.txt_data);
            const diffDays = Math.ceil(Math.abs(today - itemDate) / (1000 * 60 * 60 * 24));
            if (tempoAtual === 'HOJE') atendeTempo = diffDays <= 1;
            else if (tempoAtual === '7DIAS') atendeTempo = diffDays <= 7;
            else if (tempoAtual === '30DIAS') atendeTempo = diffDays <= 30;
        }

        const nb = !termoBusca || (item.nome || '').toLowerCase().includes(termoBusca) || (item.txt_descricao || '').toLowerCase().includes(termoBusca) || (item.txt_local || '').toLowerCase().includes(termoBusca);
        return cat && st && atendeTempo && nb;
    });

    if (filtrados.length === 0) {
        grid.innerHTML = `<div class="col-span-2 text-center text-muted py-12 bg-card border border-color rounded-xl"><p class="text-sm font-semibold">Nenhum objeto encontrado.</p></div>`;
        if (btnMais) btnMais.classList.add('hidden');
        return;
    }

    const itensPagina = filtrados.slice(0, limiteItensExibidos);
    itensPagina.forEach(item => {
        const card = document.createElement('div');
        card.className = "bg-card border border-color rounded-xl p-4 flex flex-col justify-between cursor-pointer hover:border-gray-500 transition shadow-sm hover:shadow-md relative overflow-hidden";
        card.onclick = () => abrirDetalhes(item);

        const fotosArr = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
        const imgHtml = fotosArr[0] ? `<div class="relative"><img src="${fotosArr[0]}" class="w-full h-32 object-cover rounded-lg mb-3"></div>` : `<div class="w-full h-32 bg-header border border-color rounded-lg mb-3 flex items-center justify-center text-muted"><i class="fas fa-box text-3xl"></i></div>`;
        
        const stUpper = normalizarStatus(item.status);
        let badge = 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
        if (stUpper === 'SOLICITADO') badge = 'bg-amber-900/40 text-amber-400 border-amber-700/50';
        if (stUpper === 'ENTREGUE') badge = 'bg-slate-800 text-slate-400 border-slate-700';

        card.innerHTML = `<div>${imgHtml}<div class="flex justify-between items-center mb-1 gap-2"><span class="text-[10px] font-bold dynamic-badge px-2 py-0.5 rounded uppercase">${item.categoria}</span><span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${badge}">${stUpper}</span></div><h4 class="font-bold text-base mt-2 text-main leading-tight truncate">${item.nome || item.txt_descricao}</h4><p class="text-[10px] text-muted mt-2"><i class="fas fa-calendar-alt"></i> ${item.txt_data} • <i class="fas fa-map-marker-alt"></i> ${item.txt_local}</p></div>`;
        grid.appendChild(card);
    });

    if (btnMais) {
        if (limiteItensExibidos < filtrados.length) btnMais.classList.remove('hidden');
        else btnMais.classList.add('hidden');
    }
}

function carregarMaisItens() { limiteItensExibidos += 12; renderizarItens(); }

function abrirDetalhes(item) {
    itemSelecionado = item;
    document.getElementById('catalogScreen')?.classList.add('hidden');
    document.getElementById('muralScreen')?.classList.add('hidden');
    document.getElementById('apresentacaoScreen')?.classList.add('hidden');
    document.getElementById('detailScreen')?.classList.remove('hidden');

    document.getElementById('detailTitle').innerText = item.nome || item.txt_descricao;
    document.getElementById('detailDescription').innerText = item.nome ? item.txt_descricao : '';
    document.getElementById('detailLocal').innerText = item.txt_local;
    document.getElementById('detailDate').innerText = item.txt_data;

    if (item.categoria.toUpperCase() === "ELETRÔNICOS") document.getElementById('detailRegraEletronico').classList.remove('hidden');
    else document.getElementById('detailRegraEletronico').classList.add('hidden');

    const container = document.getElementById('carouselContainer');
    const placeholder = document.getElementById('detailPlaceholder');
    const counter = document.getElementById('photoCounter');
    
    container.innerHTML = ''; fotosAtuais = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
    fotoIndiceAtual = 0;

    if (fotosAtuais.length > 0) {
        placeholder.classList.add('hidden'); container.classList.remove('hidden');
        fotosAtuais.forEach((f) => {
            const slide = document.createElement('div'); slide.className = "w-full h-full flex-shrink-0 snap-center flex items-center justify-center p-2";
            slide.innerHTML = `<img src="${f}" class="max-h-full max-w-full object-contain rounded-lg">`;
            container.appendChild(slide);
        });
        document.getElementById('photoCurrentIdx').innerText = 1; document.getElementById('photoTotalCount').innerText = fotosAtuais.length;
        counter.classList.remove('hidden');
        document.getElementById('btnPrevPhoto').classList.toggle('hidden', fotosAtuais.length <= 1);
        document.getElementById('btnNextPhoto').classList.toggle('hidden', fotosAtuais.length <= 1);
        container.onscroll = () => { if (container.clientWidth > 0) { document.getElementById('photoCurrentIdx').innerText = Math.round(container.scrollLeft / container.clientWidth) + 1; } };
    } else {
        container.classList.add('hidden'); counter.classList.add('hidden');
        document.getElementById('btnPrevPhoto').classList.add('hidden'); document.getElementById('btnNextPhoto').classList.add('hidden');
        placeholder.classList.remove('hidden');
    }

    const stUpper = normalizarStatus(item.status);
    const badgeStatus = document.getElementById('detailStatusBadge');
    badgeStatus.innerText = stUpper;
    if (stUpper === 'SOLICITADO') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-amber-900/40 text-amber-400 border-amber-700/50';
    else if (stUpper === 'ENTREGUE') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-slate-800 text-slate-400 border-slate-700';
    else badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-emerald-900/40 text-emerald-400 border-emerald-700/50';

    const btnSolicitar = document.getElementById('btnSolicitar');
    if (stUpper !== 'DISPONÍVEL') {
        btnSolicitar.disabled = true; btnSolicitar.innerText = `STATUS: ${stUpper}`;
        btnSolicitar.className = "w-full bg-gray-700 text-gray-400 cursor-not-allowed font-bold py-3.5 rounded-xl text-sm uppercase";
    } else {
        btnSolicitar.disabled = false; btnSolicitar.innerText = "ESTE É O MEU ITEM";
        btnSolicitar.className = "w-full dynamic-btn font-bold py-3.5 rounded-xl text-sm uppercase";
    }
}

function navegarFotos(direcao) {
    const container = document.getElementById('carouselContainer');
    if (!container || fotosAtuais.length === 0) return;
    fotoIndiceAtual = (fotoIndiceAtual + direcao + fotosAtuais.length) % fotosAtuais.length;
    container.scrollTo({ left: container.clientWidth * fotoIndiceAtual, behavior: 'smooth' });
}

function voltarParaCatalogo() {
    document.getElementById('detailScreen')?.classList.add('hidden');
    document.getElementById('apresentacaoScreen')?.classList.add('hidden');
    if (abaAtiva === 'mural') document.getElementById('muralScreen')?.classList.remove('hidden');
    else document.getElementById('catalogScreen')?.classList.remove('hidden');
}

// MODO APRESENTAÇÃO
function atualizarItensApresentacao() {
    apresentacaoItens = todosItens.filter(i => { const st = normalizarStatus(i.status); return st === 'DISPONÍVEL' || st === 'SOLICITADO' || st === 'PARA DOAÇÃO'; });
    if (apresentacaoItens.length === 0) apresentacaoItens = todosItens;
}

function alternarModoApresentacao() {
    modoApresentacaoAtivo = !modoApresentacaoAtivo;
    const catScreen = document.getElementById('catalogScreen');
    const muralScreen = document.getElementById('muralScreen');
    const apScreen = document.getElementById('apresentacaoScreen');
    const detScreen = document.getElementById('detailScreen');
    const btn = document.getElementById('btnModoApresentacao');

    if (modoApresentacaoAtivo) {
        atualizarItensApresentacao();
        if (apresentacaoItens.length === 0) return alert("Nenhum item para apresentar.");
        catScreen.classList.add('hidden'); muralScreen.classList.add('hidden'); detScreen.classList.add('hidden'); apScreen.classList.remove('hidden');
        btn.classList.add('border-red-500', 'text-red-500'); btn.querySelector('span').innerText = "Parar"; btn.querySelector('i').className = "fas fa-stop text-red-500";
        apresentacaoIndice = 0; exibirItemApresentacao(apresentacaoIndice); iniciarTemporizadorApresentacao();
    } else {
        pararTemporizadorApresentacao(); apScreen.classList.add('hidden');
        if (abaAtiva === 'mural') muralScreen.classList.remove('hidden'); else catScreen.classList.remove('hidden');
        btn.classList.remove('border-red-500', 'text-red-500'); btn.querySelector('span').innerText = "Apresentação"; btn.querySelector('i').className = "fas fa-play text-red-500";
    }
}

function exibirItemApresentacao(idx) {
    if (apresentacaoItens.length === 0) return;
    const item = apresentacaoItens[idx];
    const imgEl = document.getElementById('apresentacaoImg');
    const placeholderEl = document.getElementById('apresentacaoPlaceholder');
    const tituloEl = document.getElementById('apresentacaoTitulo');
    const descEl = document.getElementById('apresentacaoDescricao');
    const catEl = document.getElementById('apresentacaoCategoria');
    const localEl = document.getElementById('apresentacaoLocal');
    const dataEl = document.getElementById('apresentacaoData');
    const statusEl = document.getElementById('apresentacaoStatus');
    const regraEletronico = document.getElementById('apresentacaoRegraEletronico');

    imgEl.classList.add('opacity-0', 'scale-95');

    setTimeout(() => {
        tituloEl.innerText = item.nome || item.txt_descricao || "Sem título";
        descEl.innerText = item.nome ? item.txt_descricao : '';
        catEl.innerText = item.categoria || "OUTROS"; localEl.innerText = item.txt_local || "-"; dataEl.innerText = item.txt_data || "-";
        if (item.categoria.toUpperCase() === "ELETRÔNICOS") regraEletronico.classList.remove('hidden'); else regraEletronico.classList.add('hidden');

        const st = normalizarStatus(item.status);
        statusEl.innerText = st;
        if (st === 'SOLICITADO') statusEl.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase border bg-amber-900/40 text-amber-400 border-amber-700/50';
        else statusEl.className = 'text-xs font-bold px-3 py-1 rounded-full uppercase border bg-emerald-900/40 text-emerald-400 border-emerald-700/50';

        const fotosArr = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
        if (fotosArr.length > 0 && fotosArr[0]) {
            placeholderEl.classList.add('hidden'); imgEl.src = fotosArr[0]; imgEl.classList.remove('hidden');
        } else {
            imgEl.src = ''; imgEl.classList.add('hidden'); placeholderEl.classList.remove('hidden');
        }
        imgEl.classList.remove('opacity-0', 'scale-95'); imgEl.classList.add('opacity-100', 'scale-100');
    }, 300);
}

function navegarApresentacao(direcao) {
    if (apresentacaoItens.length === 0) return;
    apresentacaoIndice = (apresentacaoIndice + direcao + apresentacaoItens.length) % apresentacaoItens.length;
    exibirItemApresentacao(apresentacaoIndice); iniciarTemporizadorApresentacao();
}
function iniciarTemporizadorApresentacao() { pararTemporizadorApresentacao(); apresentacaoTimer = setInterval(() => { navegarApresentacao(1); }, 5000); }
function pararTemporizadorApresentacao() { if (apresentacaoTimer) { clearInterval(apresentacaoTimer); apresentacaoTimer = null; } }
function abrirDetalhesDoItemAtualApresentacao() {
    if (apresentacaoItens.length === 0) return;
    const item = apresentacaoItens[apresentacaoIndice];
    alternarModoApresentacao(); abrirDetalhes(item);
}

document.getElementById('apresentacaoCard')?.addEventListener('mouseenter', pararTemporizadorApresentacao);
document.getElementById('apresentacaoCard')?.addEventListener('mouseleave', () => { if (modoApresentacaoAtivo) iniciarTemporizadorApresentacao(); });

// MURAL E CHAT
async function enviarAvisoMural(e) {
    e.preventDefault();
    const nome = document.getElementById('muralNome').value.trim();
    const rm = document.getElementById('muralRM').value.trim();
    const categoria = document.getElementById('muralCategoria').value;
    const descricao = document.getElementById('muralDescricao').value.trim();
    const btn = document.getElementById('btnPublicarMural');

    if (!nome || !rm || !descricao) return alert("Preencha todos os campos!");

    localStorage.setItem('aluno_dados', JSON.stringify({ nome, rm }));
    btn.disabled = true; btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Enviando...`;

    try {
        const res = await fetch(`${API_URL}/api/mural`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, rm, categoria, descricao })
        });
        const resp = await res.json();
        if (res.ok && resp.success) {
            document.getElementById('muralDescricao').value = '';
            if (resp.matches_encontrados && resp.matches_encontrados.length > 0) exibirMatchesImediatos(resp.matches_encontrados);
            else alert("Aviso registrado! Você será notificado se encontrarmos.");
            carregarFeedMural();
        } else alert(resp.message || "Erro.");
    } catch (err) { alert("Erro de comunicação."); } 
    finally { btn.disabled = false; btn.innerHTML = `<i class="fas fa-paper-plane"></i> Publicar`; }
}

function exibirMatchesImediatos(itens) {
    const lista = document.getElementById('matchItensLista');
    lista.innerHTML = '';
    itens.forEach(item => {
        const card = document.createElement('div');
        card.className = "bg-header border border-color rounded-xl p-3 flex items-center justify-between gap-3";
        const fotoUrl = item.fotos && item.fotos.length > 0 ? item.fotos[0] : item.foto;
        const imgTag = fotoUrl ? `<img src="${fotoUrl}" class="w-16 h-16 object-cover rounded-lg shrink-0">` : `<div class="w-16 h-16 bg-card border border-color rounded-lg flex items-center justify-center shrink-0 text-muted"><i class="fas fa-box text-xl"></i></div>`;

        card.innerHTML = `
            <div class="flex items-center gap-3 min-w-0">
                ${imgTag}
                <div class="min-w-0"><span class="text-[10px] font-bold dynamic-badge px-2 py-0.5 rounded uppercase">${item.categoria}</span><h4 class="font-bold text-sm text-main truncate mt-1">${item.nome || item.txt_descricao}</h4></div>
            </div>
            <button onclick="selecionarMatchDirect('${item.id}')" class="dynamic-btn text-xs font-bold px-3 py-2 rounded-lg shrink-0">É MEU!</button>
        `;
        lista.appendChild(card);
    });
    document.getElementById('modalMatchImediato').classList.remove('hidden');
}

function fecharModalMatch() { document.getElementById('modalMatchImediato').classList.add('hidden'); }
function selecionarMatchDirect(itemId) {
    const item = todosItens.find(i => String(i.id) === String(itemId));
    fecharModalMatch(); if (item) abrirDetalhes(item);
}

async function carregarFeedMural() {
    const feed = document.getElementById('muralFeed');
    try {
        const res = await fetch(`${API_URL}/api/mural`);
        if (!res.ok) return;
        const avisos = await res.json();
        feed.innerHTML = '';
        avisos.forEach(a => {
            const el = document.createElement('div');
            el.className = "bg-card border border-color rounded-xl p-4 space-y-1.5";
            const st = a.status === 'LOCALIZADO' ? 'bg-emerald-900/40 text-emerald-400' : 'bg-amber-900/40 text-amber-400';
            el.innerHTML = `<div class="flex justify-between items-center text-xs"><span class="font-bold text-main">${a.nome_aluno}</span><span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase border border-color ${st}">${a.status}</span></div><p class="text-xs text-muted italic">"${a.descricao}"</p>`;
            feed.appendChild(el);
        });
    } catch (e) {}
}

async function verificarNotificacoesAutomaticas() {
    const salvo = JSON.parse(localStorage.getItem('aluno_dados') || '{}');
    if (!salvo.rm) return;
    try {
        const res = await fetch(`${API_URL}/api/mural/notificacoes/${salvo.rm}`);
        if (res.ok) {
            const notifs = await res.json();
            const badge = document.getElementById('badgeNotificacaoMural');
            if (notifs && notifs.length > 0) { badge.classList.remove('hidden'); badge.innerText = notifs.length; } 
            else badge.classList.add('hidden');
        }
    } catch (e) {}
}

function alternarJanelaChat() {
    chatAberto = !chatAberto;
    const janela = document.getElementById('janelaChat');
    const badge = document.getElementById('badgeChatWeb');
    if (chatAberto) {
        janela.classList.remove('hidden'); badge.classList.add('hidden');
        const salvo = JSON.parse(localStorage.getItem('aluno_dados') || '{}');
        if (salvo.nome) document.getElementById('chatInputNome').value = salvo.nome;
        if (salvo.rm) document.getElementById('chatInputRM').value = salvo.rm;
        atualizarMensagensChat(); iniciarPollingChat();
    } else {
        janela.classList.add('hidden'); pararPollingChat();
    }
}

function abrirChatComItem() {
    if (!chatAberto) alternarJanelaChat();
    if (itemSelecionado) {
        const i = document.getElementById('chatInputTexto');
        i.value = `Dúvida sobre o item #${itemSelecionado.id}: `; i.focus();
    }
}

function iniciarPollingChat() { pararPollingChat(); chatTimerPolling = setInterval(atualizarMensagensChat, 3000); }
function pararPollingChat() { if (chatTimerPolling) clearInterval(chatTimerPolling); chatTimerPolling = null; }

async function atualizarMensagensChat() {
    const rm = document.getElementById('chatInputRM').value.trim();
    if (!rm) return;
    try {
        const res = await fetch(`${API_URL}/api/chat/mensagens/${rm}?marcar_lida=true&origem=ALUNO`);
        if (!res.ok) return;
        const mensagens = await res.json();
        const container = document.getElementById('chatMensagens');
        if (mensagens.length !== ultimaQtdMensagens) {
            ultimaQtdMensagens = mensagens.length; container.innerHTML = '';
            mensagens.forEach(m => {
                const eu = m.remetente === 'ALUNO';
                const div = document.createElement('div');
                div.className = `flex flex-col ${eu ? 'items-end' : 'items-start'}`;
                const balao = eu ? 'bg-red-600 text-white rounded-tr-none' : 'bg-header border border-color text-main rounded-tl-none';
                div.innerHTML = `<span class="text-[9px] text-muted mb-0.5">${eu ? 'Você' : 'Secretaria'} • ${m.data_envio.split(' ')[1] || ''}</span><div class="max-w-[80%] px-3 py-2 rounded-2xl ${balao} shadow-sm break-words">${m.mensagem}</div>`;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {}
}

async function enviarMensagemChat(e) {
    e.preventDefault();
    const nome = document.getElementById('chatInputNome').value.trim();
    const rm = document.getElementById('chatInputRM').value.trim();
    const inputTexto = document.getElementById('chatInputTexto');
    if (!rm || !nome || !inputTexto.value.trim()) return;
    localStorage.setItem('aluno_dados', JSON.stringify({ nome, rm }));
    try {
        const res = await fetch(`${API_URL}/api/chat/enviar`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rm, nome, remetente: 'ALUNO', mensagem: inputTexto.value.trim() })
        });
        if (res.ok) { inputTexto.value = ''; atualizarMensagensChat(); }
    } catch (err) {}
}

// SOLICITAÇÃO COM PROVA DE PROPRIEDADE
function abrirModalSolicitacao() {
    if (!itemSelecionado) return;
    const salvo = JSON.parse(localStorage.getItem('aluno_dados') || '{}');
    if (salvo.nome) document.getElementById('solicitaNome').value = salvo.nome;
    if (salvo.rm) document.getElementById('solicitaRM').value = salvo.rm;
    document.getElementById('solicitaProva').value = '';
    document.getElementById('solicitaMsgErro').classList.add('hidden');
    document.getElementById('modalSolicitacao').classList.remove('hidden');
}

function fecharModalSolicitacao() { document.getElementById('modalSolicitacao').classList.add('hidden'); }

async function enviarSolicitacao() {
    const nome = document.getElementById('solicitaNome').value.trim();
    const rm = document.getElementById('solicitaRM').value.trim();
    const prova = document.getElementById('solicitaProva').value.trim();
    const erroEl = document.getElementById('solicitaMsgErro');
    const btn = document.getElementById('btnConfirmarSolicitacao');
    
    if (!nome || !rm || !prova) { erroEl.innerText = "Preencha o Nome, RM e a Prova de Propriedade!"; erroEl.classList.remove('hidden'); return; }
    btn.disabled = true; btn.innerHTML = `Enviando...`;
    
    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: itemSelecionado.id, nome, rm, prova })
        });
        const res = await response.json();
        if (response.ok && res.success) {
            localStorage.setItem('aluno_dados', JSON.stringify({ nome, rm }));
            alert(res.message);
            fecharModalSolicitacao();
            voltarParaCatalogo();
            carregarItensDaAPI();
        } else { erroEl.innerText = res.message; erroEl.classList.remove('hidden'); }
    } catch (err) { erroEl.innerText = "Erro."; erroEl.classList.remove('hidden'); } 
    finally { btn.disabled = false; btn.innerHTML = `Confirmar Pedido`; }
}

window.onload = () => {
    carregarPreferenciasAparencia();
    carregarCategoriasDinamicamente();
    carregarItensDaAPI();
    
    const salvo = JSON.parse(localStorage.getItem('aluno_dados') || '{}');
    if (salvo.nome) { if(document.getElementById('chatInputNome')) document.getElementById('chatInputNome').value = salvo.nome; }
    if (salvo.rm) { if(document.getElementById('chatInputRM')) document.getElementById('chatInputRM').value = salvo.rm; }
    setTimeout(() => { const dBtn = document.querySelector('.cat-btn'); if (dBtn) moveIndicator(dBtn); }, 200);
};

window.addEventListener('resize', () => {
    const actBtn = document.querySelector('.cat-btn.text-white');
    if (actBtn) moveIndicator(actBtn);
});
