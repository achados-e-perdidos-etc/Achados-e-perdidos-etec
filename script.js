const API_URL = ""; 
let alunoLogado = null;
let acaoPendente = null; // Armazena 'solicitar' ou 'publicar' caso o aluno não esteja identificado

let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let termoBusca = '';
let fotosAtuais = [];
let fotoIndiceAtual = 0;
let avisosMural = [];

// ==========================================
// 1. INICIALIZAÇÃO E SESSÃO DO USUÁRIO
// ==========================================

window.onload = () => {
    carregarPreferenciasAparencia();
    carregarItensDaAPI();
    carregarMuralAPI();
    checarIdentificacaoSalva();

    setTimeout(() => {
        const defaultBtn = document.querySelector('.cat-btn');
        if (defaultBtn) moveIndicator(defaultBtn);
    }, 100);
};

function checarIdentificacaoSalva() {
    const salvo = localStorage.getItem('aluno_sessao');
    if (salvo) {
        try {
            alunoLogado = JSON.parse(salvo);
            atualizarUIUsuario();
            carregarNotificacoes();
        } catch (e) {
            localStorage.removeItem('aluno_sessao');
        }
    }
}

function atualizarUIUsuario() {
    const userInfo = document.getElementById('userInfo');
    const userName = document.getElementById('userName');
    const userRM = document.getElementById('userRM');
    const btnNotif = document.getElementById('btnNotificacoes');

    if (alunoLogado) {
        userName.innerText = alunoLogado.nome;
        userRM.innerText = `RM: ${alunoLogado.rm}`;
        userInfo.classList.remove('hidden');
        btnNotif.classList.remove('hidden');
    } else {
        userInfo.classList.add('hidden');
        btnNotif.classList.add('hidden');
    }
}

function logout() {
    alunoLogado = null;
    localStorage.removeItem('aluno_sessao');
    atualizarUIUsuario();
    mostrarAviso('Desconectado', 'Seus dados foram removidos deste dispositivo.', 'info');
}

// ==========================================
// 2. MODAL DE IDENTIFICAÇÃO SILENCIOSA
// ==========================================

function abrirModalIdentificacao(acao = null) {
    acaoPendente = acao;
    const modal = document.getElementById('modalIdentificacao');
    const content = document.getElementById('modalIdentificacaoContent');
    const errorMsg = document.getElementById('modalIdError');
    
    document.getElementById('inputIdNome').value = alunoLogado ? alunoLogado.nome : '';
    document.getElementById('inputIdRm').value = alunoLogado ? alunoLogado.rm : '';
    errorMsg.classList.add('hidden');
    
    // Reseta botão
    const btnConfirmar = document.getElementById('btnConfirmarId');
    btnConfirmar.disabled = false;
    btnConfirmar.classList.remove('opacity-70', 'cursor-not-allowed');
    document.getElementById('btnConfirmarIdText').innerText = 'Salvar e Continuar';
    document.getElementById('btnConfirmarIdSpinner').classList.add('hidden');

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);
}

function fecharModalIdentificacao() {
    const modal = document.getElementById('modalIdentificacao');
    const content = document.getElementById('modalIdentificacaoContent');
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}

async function confirmarIdentificacao() {
    const nome = document.getElementById('inputIdNome').value.trim();
    const rm = document.getElementById('inputIdRm').value.trim();
    const errorMsg = document.getElementById('modalIdError');

    if (!nome || !rm || rm.length < 4) {
        errorMsg.innerText = "Preencha um Nome e um RM válido!";
        errorMsg.classList.remove('hidden');
        return;
    }
    errorMsg.classList.add('hidden');

    const btnConfirmar = document.getElementById('btnConfirmarId');
    btnConfirmar.disabled = true;
    btnConfirmar.classList.add('opacity-70', 'cursor-not-allowed');
    document.getElementById('btnConfirmarIdText').innerText = 'Salvando...';
    document.getElementById('btnConfirmarIdSpinner').classList.remove('hidden');

    try {
        const response = await fetch(`${API_URL}/api/usuario/identificar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, rm })
        });
        const res = await response.json();

        if (response.ok && res.success) {
            alunoLogado = res.usuario;
            localStorage.setItem('aluno_sessao', JSON.stringify(alunoLogado));
            atualizarUIUsuario();
            carregarNotificacoes();
            fecharModalIdentificacao();

            // Executa a ação que o aluno queria fazer
            setTimeout(() => {
                if (acaoPendente === 'solicitar') {
                    abrirModalSolicitar();
                } else if (acaoPendente === 'publicar') {
                    document.getElementById('btnPublicarAviso').click(); // Re-dispara a publicação
                }
                acaoPendente = null;
            }, 400);

        } else {
            errorMsg.innerText = res.message || "Erro ao salvar identificação.";
            errorMsg.classList.remove('hidden');
            btnConfirmar.disabled = false;
        }
    } catch (err) {
        errorMsg.innerText = "Erro de conexão com o servidor.";
        errorMsg.classList.remove('hidden');
        btnConfirmar.disabled = false;
        btnConfirmar.classList.remove('opacity-70', 'cursor-not-allowed');
        document.getElementById('btnConfirmarIdText').innerText = 'Salvar e Continuar';
        document.getElementById('btnConfirmarIdSpinner').classList.add('hidden');
    }
}

// ==========================================
// 3. FLUXO DE SOLICITAR COLETA
// ==========================================

function processarBotaoSolicitar() {
    if (!itemSelecionado) return;
    const stUpper = normalizarStatus(itemSelecionado.status);
    if (stUpper !== 'DISPONÍVEL') {
        mostrarAviso('Atenção', 'Este item não está mais disponível para solicitação.', 'erro');
        return;
    }
    
    // Pede nome e rm na hora se nao estiver logado
    if (!alunoLogado) {
        abrirModalIdentificacao('solicitar');
    } else {
        abrirModalSolicitar();
    }
}

function abrirModalSolicitar() {
    const modal = document.getElementById('modalSolicitar');
    const content = document.getElementById('modalSolicitarContent');
    
    document.getElementById('resumoSolicitanteNome').innerText = alunoLogado.nome;
    document.getElementById('resumoSolicitanteRm').innerText = alunoLogado.rm;

    const btnConfirmar = document.getElementById('btnConfirmarSolicitacao');
    btnConfirmar.disabled = false;
    btnConfirmar.classList.remove('opacity-70', 'cursor-not-allowed');
    document.getElementById('btnConfirmarText').innerText = 'Confirmar';
    document.getElementById('btnConfirmarSpinner').classList.add('hidden');

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);
}

function fecharModalSolicitar() {
    const modal = document.getElementById('modalSolicitar');
    const content = document.getElementById('modalSolicitarContent');
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}

async function confirmarSolicitacao() {
    const btnConfirmar = document.getElementById('btnConfirmarSolicitacao');
    btnConfirmar.disabled = true;
    btnConfirmar.classList.add('opacity-70', 'cursor-not-allowed');
    document.getElementById('btnConfirmarText').innerText = 'Enviando...';
    document.getElementById('btnConfirmarSpinner').classList.remove('hidden');

    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: itemSelecionado.id,
                nome: alunoLogado.nome,
                rm: alunoLogado.rm
            })
        });

        const res = await response.json();
        fecharModalSolicitar(); 

        if (response.ok && res.success) {
            setTimeout(() => {
                mostrarAviso('Solicitação Concluída!', res.message, 'sucesso');
                voltarParaCatalogo();
                carregarItensDaAPI();
            }, 300);
        } else {
            setTimeout(() => {
                mostrarAviso('Erro na Solicitação', res.message || "Não foi possível realizar a solicitação.", 'erro');
            }, 300);
        }
    } catch (error) {
        fecharModalSolicitar();
        setTimeout(() => {
            mostrarAviso('Erro de Conexão', 'Não foi possível conectar ao servidor. Tente novamente.', 'erro');
        }, 300);
    }
}

// ==========================================
// 4. MURAL DE PERDIDOS E MATCH INTELIGENTE
// ==========================================

function alternarAba(aba) {
    const tabCat = document.getElementById('tabCatalogo');
    const tabMur = document.getElementById('tabMural');
    const screenCat = document.getElementById('catalogScreen');
    const screenMur = document.getElementById('muralScreen');
    const screenDet = document.getElementById('detailScreen');

    if (aba === 'catalogo') {
        tabCat.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all bg-card text-main shadow-sm";
        tabMur.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all text-muted hover:text-main";
        screenMur.classList.add('hidden');
        screenDet.classList.add('hidden');
        screenCat.classList.remove('hidden');
        carregarItensDaAPI();
    } else {
        tabMur.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all bg-card text-main shadow-sm";
        tabCat.className = "px-4 py-1.5 rounded-lg text-xs font-bold transition-all text-muted hover:text-main";
        screenCat.classList.add('hidden');
        screenDet.classList.add('hidden');
        screenMur.classList.remove('hidden');
        carregarMuralAPI();
    }
}

async function carregarMuralAPI() {
    try {
        const response = await fetch(`${API_URL}/api/avisos`);
        if (response.ok) {
            avisosMural = await response.json();
            renderizarMural();
        }
    } catch (error) {
        console.error("Erro ao carregar avisos:", error);
    }
}

function renderizarMural() {
    const grid = document.getElementById('muralGrid');
    if (!grid) return;
    grid.innerHTML = '';

    if (avisosMural.length === 0) {
        grid.innerHTML = `
            <div class="col-span-2 text-center text-muted py-12 bg-card border border-color rounded-xl">
                <i class="fas fa-wind text-3xl mb-2 text-muted"></i>
                <p class="text-sm font-semibold">Nenhum aviso no mural ainda.</p>
            </div>`;
        return;
    }

    avisosMural.forEach(aviso => {
        const card = document.createElement('div');
        card.className = "bg-header border border-color rounded-xl p-4 relative overflow-hidden";
        
        if (alunoLogado && aviso.rm_aluno === alunoLogado.rm) {
            card.classList.add('border-amber-500/50', 'bg-amber-500/5');
            card.innerHTML = `<span class="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-amber-500"></span>`;
        }

        card.innerHTML += `
            <div class="flex justify-between items-start mb-2">
                <span class="text-[10px] font-bold bg-card border border-color px-2 py-0.5 rounded text-muted uppercase">${aviso.categoria}</span>
                <span class="text-[10px] font-bold text-muted"><i class="far fa-clock"></i> ${aviso.data_aviso}</span>
            </div>
            <p class="text-sm text-main font-semibold mb-3">"${aviso.descricao}"</p>
            <div class="flex items-center gap-2 pt-3 border-t border-color/50">
                <div class="w-6 h-6 rounded-full bg-card border border-color flex items-center justify-center text-xs text-muted">
                    <i class="fas fa-user"></i>
                </div>
                <span class="text-xs text-muted">Procurado por <strong>${aviso.nome_aluno.split(' ')[0]}</strong></span>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function publicarAvisoMural(e) {
    e.preventDefault();
    if (!alunoLogado) {
        abrirModalIdentificacao('publicar');
        return;
    }

    const descricao = document.getElementById('avisoDescricao').value.trim();
    const categoria = document.getElementById('avisoCategoria').value;
    const btn = document.getElementById('btnPublicarAviso');

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    document.getElementById('btnPublicarText').innerText = 'Publicando...';
    document.getElementById('btnPublicarSpinner').classList.remove('hidden');

    try {
        const response = await fetch(`${API_URL}/api/avisos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome: alunoLogado.nome,
                rm: alunoLogado.rm,
                descricao: descricao,
                categoria: categoria
            })
        });

        const res = await response.json();
        
        if (response.ok && res.success) {
            document.getElementById('avisoDescricao').value = '';
            carregarMuralAPI(); 
            
            // MATCH IMEDIATO!
            if (res.matches_encontrados && res.matches_encontrados.length > 0) {
                mostrarModalMatch(res.matches_encontrados);
            } else {
                mostrarAviso('Aviso Publicado!', 'Sua postagem está no mural. Te avisaremos se encontrarmos!', 'sucesso');
            }
        } else {
            mostrarAviso('Erro', res.message, 'erro');
        }
    } catch (err) {
        mostrarAviso('Erro', 'Falha ao conectar no servidor', 'erro');
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        document.getElementById('btnPublicarText').innerText = 'Publicar no Mural';
        document.getElementById('btnPublicarSpinner').classList.add('hidden');
    }
}

function mostrarModalMatch(matches) {
    const modal = document.getElementById('modalMatch');
    const content = document.getElementById('modalMatchContent');
    const container = document.getElementById('matchItemsContainer');
    
    container.innerHTML = '';
    
    matches.forEach(item => {
        const foto = (item.fotos && item.fotos.length > 0) ? item.fotos[0] : '';
        const imgHtml = foto 
            ? `<img src="${foto}" class="w-12 h-12 object-cover rounded-lg shrink-0">`
            : `<div class="w-12 h-12 bg-card border border-color rounded-lg flex items-center justify-center text-muted shrink-0"><i class="fas fa-box"></i></div>`;
            
        container.innerHTML += `
            <div class="flex items-center gap-3 p-3 bg-header border border-color rounded-xl cursor-pointer hover:border-amber-500 transition" onclick="abrirDetalhesDoMatch(${item.id})">
                ${imgHtml}
                <div>
                    <h4 class="text-sm font-bold text-main line-clamp-1">${item.txt_descricao}</h4>
                    <p class="text-[10px] text-muted"><i class="fas fa-map-marker-alt"></i> ${item.txt_local} | ${item.txt_data}</p>
                </div>
            </div>
        `;
    });

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);
}

function fecharModalMatch() {
    const modal = document.getElementById('modalMatch');
    const content = document.getElementById('modalMatchContent');
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}

function irParaCatalogoAposMatch() {
    fecharModalMatch();
    alternarAba('catalogo');
}

function abrirDetalhesDoMatch(id) {
    const item = todosItens.find(i => i.id === id);
    if (item) {
        fecharModalMatch();
        alternarAba('catalogo');
        abrirDetalhes(item);
    }
}

// ==========================================
// 5. SISTEMA DE NOTIFICAÇÕES (SININHO)
// ==========================================

async function carregarNotificacoes() {
    if (!alunoLogado) return;
    try {
        const response = await fetch(`${API_URL}/api/notificacoes/${alunoLogado.rm}`);
        if (response.ok) {
            const notifs = await response.json();
            const badge = document.getElementById('badgeNotificacao');
            
            if (notifs.length > 0) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }

            const lista = document.getElementById('listaNotificacoes');
            lista.innerHTML = '';
            
            if (notifs.length === 0) {
                lista.innerHTML = `<p class="text-xs text-muted text-center py-6">Nenhuma notificação nova.</p>`;
                return;
            }

            notifs.forEach(n => {
                lista.innerHTML += `
                    <div class="bg-header border border-color p-3 rounded-xl relative cursor-pointer hover:border-amber-500 transition" onclick="lerNotificacao(${n.id})">
                        <span class="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-red-500"></span>
                        <h4 class="text-sm font-bold text-main mb-1">${n.titulo}</h4>
                        <p class="text-xs text-muted leading-relaxed">${n.mensagem}</p>
                        <p class="text-[9px] text-muted mt-2 uppercase font-bold"><i class="far fa-clock"></i> ${n.data_criacao}</p>
                    </div>
                `;
            });
        }
    } catch (e) { console.error("Erro nas notificações", e); }
}

function abrirModalNotificacoes() {
    const modal = document.getElementById('modalNotificacoes');
    const content = document.getElementById('modalNotificacoesContent');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);
}

function fecharModalNotificacoes() {
    const modal = document.getElementById('modalNotificacoes');
    const content = document.getElementById('modalNotificacoesContent');
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}

async function lerNotificacao(id) {
    try {
        await fetch(`${API_URL}/api/notificacoes/${id}/ler`, { method: 'PUT' });
        carregarNotificacoes(); // Atualiza a lista e o sininho
        fecharModalNotificacoes();
        alternarAba('catalogo'); // Manda o aluno pro catálogo procurar o item dele
    } catch (e) { console.error(e); }
}

// ==========================================
// 6. ROTINAS DO CATÁLOGO E DETALHES GERAIS
// ==========================================

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
    const label = document.getElementById('themeLabel');
    const icon = document.getElementById('themeIcon');
    const isLight = document.body.classList.contains('light-theme');

    if (isLight) {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        if (label) label.innerText = "Modo Escuro";
        if (icon) icon.className = "fas fa-moon text-yellow-400";
        localStorage.setItem('theme_mode', 'dark');
    } else {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        if (label) label.innerText = "Modo Claro";
        if (icon) icon.className = "fas fa-sun text-yellow-500";
        localStorage.setItem('theme_mode', 'light');
    }
}

function carregarPreferenciasAparencia() {
    aplicarTemaVermelho();
    const modoSalvo = localStorage.getItem('theme_mode') || 'dark';
    const label = document.getElementById('themeLabel');
    const icon = document.getElementById('themeIcon');

    if (modoSalvo === 'light') {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        if (label) label.innerText = "Modo Claro";
        if (icon) icon.className = "fas fa-sun text-yellow-500";
    } else {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        if (label) label.innerText = "Modo Escuro";
        if (icon) icon.className = "fas fa-moon text-yellow-400";
    }
}

window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.cat-btn.text-white');
    if (activeBtn) moveIndicator(activeBtn);
});

function filtrarPorPalavraChave() {
    const input = document.getElementById('searchInput');
    const btnClear = document.getElementById('btnClearSearch');
    termoBusca = input.value.trim().toLowerCase();
    if (btnClear) btnClear.classList.toggle('hidden', termoBusca.length === 0);
    renderizarItens();
}

function limparBusca() {
    const input = document.getElementById('searchInput');
    if (input) input.value = '';
    termoBusca = '';
    document.getElementById('btnClearSearch')?.classList.add('hidden');
    renderizarItens();
}

function filtrarStatus(status) {
    statusAtual = status;
    renderizarItens();
}

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
            b.classList.remove('text-white', 'border-transparent');
            b.classList.add('text-muted', 'border-color', 'bg-card');
        });
        btnElement.classList.remove('text-muted', 'border-color', 'bg-card');
        btnElement.classList.add('text-white', 'border-transparent');
        moveIndicator(btnElement);
    }
    renderizarItens();
}

function normalizarStatus(status) {
    let st = (status || 'DISPONÍVEL').toUpperCase();
    if (st === 'GUARDADO') return 'DISPONÍVEL';
    return st;
}

function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    if (!grid) return;
    grid.innerHTML = '';

    const filtrados = todosItens.filter(item => {
        const atendeCategoria = categoriaAtual === 'TODOS' || (item.categoria && item.categoria.toUpperCase() === categoriaAtual);
        const stUpper = normalizarStatus(item.status);
        const stFiltro = normalizarStatus(statusAtual);
        const atendeStatus = statusAtual === 'TODOS' || stUpper === stFiltro;
        const desc = (item.txt_descricao || '').toLowerCase();
        const local = (item.txt_local || '').toLowerCase();
        const cat = (item.categoria || '').toLowerCase();
        const atendeBusca = !termoBusca || desc.includes(termoBusca) || local.includes(termoBusca) || cat.includes(termoBusca);
        return atendeCategoria && atendeStatus && atendeBusca;
    });

    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div class="col-span-2 text-center text-muted py-12 bg-card border border-color rounded-xl">
                <i class="fas fa-search text-3xl mb-2 text-muted"></i>
                <p class="text-sm font-semibold">Nenhum objeto encontrado.</p>
            </div>
        `;
        return;
    }

    filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = "bg-card border border-color rounded-xl p-4 flex flex-col justify-between cursor-pointer hover:border-gray-500 transition shadow-sm";
        card.onclick = () => abrirDetalhes(item);

        const fotosArr = item.fotos && item.fotos.length > 0 ? item.fotos : [];
        const primeiraFoto = fotosArr[0];

        const imgHtml = primeiraFoto 
            ? `<div class="relative"><img src="${primeiraFoto}" class="w-full h-32 object-cover rounded-lg mb-3">${fotosArr.length > 1 ? `<span class="absolute bottom-4 right-2 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full"><i class="fas fa-images"></i> 1/${fotosArr.length}</span>` : ''}</div>`
            : `<div class="w-full h-32 bg-header border border-color rounded-lg mb-3 flex items-center justify-center text-muted"><i class="fas fa-box text-3xl"></i></div>`;

        const stUpper = normalizarStatus(item.status);
        let statusBadgeClass = 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
        
        if (stUpper === 'SOLICITADO') statusBadgeClass = 'bg-amber-900/40 text-amber-400 border-amber-700/50';
        else if (stUpper === 'ENTREGUE') statusBadgeClass = 'bg-slate-800 text-slate-400 border-slate-700';
        else if (stUpper === 'PARA DOAÇÃO' || stUpper === 'PARA DOACAO') statusBadgeClass = 'bg-purple-900/40 text-purple-400 border-purple-700/50';
        else if (stUpper === 'DOAÇÃO FEITA' || stUpper === 'DOACAO FEITA') statusBadgeClass = 'bg-pink-900/40 text-pink-400 border-pink-700/50';

        card.innerHTML = `
            <div>
                ${imgHtml}
                <div class="flex justify-between items-center mb-1 gap-2">
                    <span class="text-[10px] font-bold dynamic-badge px-2 py-0.5 rounded uppercase">${item.categoria}</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${statusBadgeClass}">${stUpper}</span>
                </div>
                <h4 class="font-bold text-base mt-2 text-main">${item.txt_descricao}</h4>
                <p class="text-xs text-muted mt-1"><i class="fas fa-map-marker-alt"></i> ${item.txt_local}</p>
            </div>
        `;
        grid.appendChild(card);
    });
}

function abrirDetalhes(item) {
    itemSelecionado = item;
    document.getElementById('catalogScreen')?.classList.add('hidden');
    document.getElementById('detailScreen')?.classList.remove('hidden');

    document.getElementById('detailTitle').innerText = item.txt_descricao;
    document.getElementById('detailDescription').innerText = item.categoria;
    document.getElementById('detailLocal').innerText = item.txt_local;
    document.getElementById('detailDate').innerText = item.txt_data;

    const container = document.getElementById('carouselContainer');
    const placeholder = document.getElementById('detailPlaceholder');
    const counter = document.getElementById('photoCounter');
    const btnPrev = document.getElementById('btnPrevPhoto');
    const btnNext = document.getElementById('btnNextPhoto');
    const btnSolicitar = document.getElementById('btnSolicitar');
    const badgeStatus = document.getElementById('detailStatusBadge');

    container.innerHTML = '';
    fotosAtuais = item.fotos && item.fotos.length > 0 ? item.fotos : [];
    fotoIndiceAtual = 0;

    if (fotosAtuais.length > 0) {
        placeholder.classList.add('hidden');
        container.classList.remove('hidden');

        fotosAtuais.forEach((f) => {
            const slide = document.createElement('div');
            slide.className = "w-full h-full flex-shrink-0 snap-center flex items-center justify-center p-2";
            slide.innerHTML = `<img src="${f}" class="max-h-full max-w-full object-contain rounded-lg">`;
            container.appendChild(slide);
        });

        document.getElementById('photoCurrentIdx').innerText = 1;
        document.getElementById('photoTotalCount').innerText = fotosAtuais.length;
        counter.classList.remove('hidden');

        btnPrev.classList.toggle('hidden', fotosAtuais.length <= 1);
        btnNext.classList.toggle('hidden', fotosAtuais.length <= 1);

        container.onscroll = () => {
            const width = container.clientWidth;
            if (width > 0) {
                const idx = Math.round(container.scrollLeft / width);
                fotoIndiceAtual = idx;
                document.getElementById('photoCurrentIdx').innerText = idx + 1;
            }
        };
    } else {
        container.classList.add('hidden');
        counter.classList.add('hidden');
        btnPrev.classList.add('hidden');
        btnNext.classList.add('hidden');
        placeholder.classList.remove('hidden');
    }

    const stUpper = normalizarStatus(item.status);
    
    if (badgeStatus) {
        badgeStatus.innerText = stUpper;
        if (stUpper === 'SOLICITADO') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-amber-900/40 text-amber-400 border-amber-700/50';
        else if (stUpper === 'ENTREGUE') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-slate-800 text-slate-400 border-slate-700';
        else if (stUpper === 'PARA DOAÇÃO' || stUpper === 'PARA DOACAO') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-purple-900/40 text-purple-400 border-purple-700/50';
        else if (stUpper === 'DOAÇÃO FEITA' || stUpper === 'DOACAO FEITA') badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-pink-900/40 text-pink-400 border-pink-700/50';
        else badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
    }

    if (stUpper !== 'DISPONÍVEL') {
        btnSolicitar.disabled = true;
        btnSolicitar.innerText = `ITEM EM STATUS: ${stUpper}`;
        btnSolicitar.className = "w-full bg-header text-muted cursor-not-allowed font-bold py-3.5 rounded-xl text-sm uppercase border border-color";
    } else {
        btnSolicitar.disabled = false;
        btnSolicitar.innerText = "ESTE É O MEU ITEM / SOLICITAR COLETA";
        btnSolicitar.className = "w-full dynamic-btn font-bold py-3.5 rounded-xl text-sm uppercase transition";
    }
}

function navegarFotos(direcao) {
    const container = document.getElementById('carouselContainer');
    if (!container || fotosAtuais.length === 0) return;
    let novoIndice = fotoIndiceAtual + direcao;
    if (novoIndice < 0) novoIndice = fotosAtuais.length - 1;
    if (novoIndice >= fotosAtuais.length) novoIndice = 0;
    fotoIndiceAtual = novoIndice;
    const width = container.clientWidth;
    container.scrollTo({ left: width * novoIndice, behavior: 'smooth' });
}

function voltarParaCatalogo() {
    document.getElementById('detailScreen')?.classList.add('hidden');
    document.getElementById('catalogScreen')?.classList.remove('hidden');
}

// ==========================================
// FUNÇÕES DE UI CUSTOMIZADA (MODAIS)
// ==========================================

function mostrarAviso(titulo, mensagem, tipo = 'sucesso') {
    const modal = document.getElementById('modalAviso');
    const content = document.getElementById('modalAvisoContent');
    const icone = document.getElementById('modalAvisoIcon');
    const tituloEl = document.getElementById('modalAvisoTitulo');
    const msgEl = document.getElementById('modalAvisoMensagem');

    modal.classList.remove('hidden');
    
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);

    tituloEl.innerText = titulo;
    msgEl.innerText = mensagem;

    if (tipo === 'sucesso') icone.innerHTML = '<i class="fas fa-check-circle text-green-500"></i>';
    else if (tipo === 'erro') icone.innerHTML = '<i class="fas fa-exclamation-circle text-red-500"></i>';
    else icone.innerHTML = '<i class="fas fa-info-circle text-blue-500"></i>';
}

function fecharModalAviso() {
    const modal = document.getElementById('modalAviso');
    const content = document.getElementById('modalAvisoContent');
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => { modal.classList.add('hidden'); }, 300);
}
