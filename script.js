const API_URL = "https://achados-etec-api.onrender.com";
let alunoLogado = null;
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let termoBusca = '';
let fotosAtuais = [];
let fotoIndiceAtual = 0;

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

async function carregarItensDaAPI() {
    try {
        const response = await fetch(`${API_URL}/api/itens`);
        if (response.ok) {
            todosItens = await response.json();
            renderizarItens();
        }
    } catch (error) {
        console.error("Erro ao carregar itens da API:", error);
    }
}

function logout() {
    alunoLogado = null;
    document.getElementById('userInfo')?.classList.add('hidden');
    document.getElementById('catalogScreen')?.classList.add('hidden');
    document.getElementById('detailScreen')?.classList.add('hidden');
}

function filtrarPorPalavraChave() {
    const input = document.getElementById('searchInput');
    const btnClear = document.getElementById('btnClearSearch');
    
    termoBusca = input.value.trim().toLowerCase();

    if (termoBusca.length > 0) {
        btnClear?.classList.remove('hidden');
    } else {
        btnClear?.classList.add('hidden');
    }

    renderizarItens();
}

function limparBusca() {
    const input = document.getElementById('searchInput');
    const btnClear = document.getElementById('btnClearSearch');
    
    if (input) input.value = '';
    termoBusca = '';
    btnClear?.classList.add('hidden');
    
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
        const atendeCategoria = categoriaAtual === 'TODOS' || 
            (item.categoria && item.categoria.toUpperCase() === categoriaAtual);

        const stUpper = normalizarStatus(item.status);
        const stFiltro = normalizarStatus(statusAtual);

        const atendeStatus = statusAtual === 'TODOS' || stUpper === stFiltro;

        const desc = (item.txt_descricao || '').toLowerCase();
        const local = (item.txt_local || '').toLowerCase();
        const cat = (item.categoria || '').toLowerCase();
        
        const atendeBusca = !termoBusca || 
            desc.includes(termoBusca) || 
            local.includes(termoBusca) || 
            cat.includes(termoBusca);

        return atendeCategoria && atendeStatus && atendeBusca;
    });

    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div class="col-span-2 text-center text-muted py-12 bg-card border border-color rounded-xl">
                <i class="fas fa-search text-3xl mb-2 text-muted"></i>
                <p class="text-sm font-semibold">Nenhum objeto encontrado.</p>
                <p class="text-xs text-muted mt-1">Tente pesquisar com outros termos ou altere os filtros selecionados.</p>
            </div>
        `;
        return;
    }

    filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = "bg-card border border-color rounded-xl p-4 flex flex-col justify-between cursor-pointer hover:border-gray-500 transition";
        card.onclick = () => abrirDetalhes(item);

        const fotosArr = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
        const primeiraFoto = fotosArr[0];

        const imgHtml = primeiraFoto 
            ? `<div class="relative"><img src="${primeiraFoto}" class="w-full h-32 object-cover rounded-lg mb-3">${fotosArr.length > 1 ? `<span class="absolute bottom-4 right-2 bg-black/70 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full"><i class="fas fa-images"></i> 1/${fotosArr.length}</span>` : ''}</div>`
            : `<div class="w-full h-32 bg-header border border-color rounded-lg mb-3 flex items-center justify-center text-muted"><i class="fas fa-box text-3xl"></i></div>`;

        const stUpper = normalizarStatus(item.status);
        let statusBadgeClass = 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
        
        if (stUpper === 'SOLICITADO') {
            statusBadgeClass = 'bg-amber-900/40 text-amber-400 border-amber-700/50';
        } else if (stUpper === 'ENTREGUE') {
            statusBadgeClass = 'bg-slate-800 text-slate-400 border-slate-700';
        } else if (stUpper === 'PARA DOAÇÃO' || stUpper === 'PARA DOACAO') {
            statusBadgeClass = 'bg-purple-900/40 text-purple-400 border-purple-700/50';
        } else if (stUpper === 'DOAÇÃO FEITA' || stUpper === 'DOACAO FEITA') {
            statusBadgeClass = 'bg-pink-900/40 text-pink-400 border-pink-700/50';
        }

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

    document.getElementById('detailTitle').innerText = item.categoria;
    document.getElementById('detailDescription').innerText = item.txt_descricao;
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
    fotosAtuais = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
    fotoIndiceAtual = 0;

    if (fotosAtuais.length > 0) {
        placeholder.classList.add('hidden');
        container.classList.remove('hidden');

        fotosAtuais.forEach((f, idx) => {
            const slide = document.createElement('div');
            slide.className = "w-full h-full flex-shrink-0 snap-center flex items-center justify-center p-2";
            slide.innerHTML = `<img src="${f}" class="max-h-full max-w-full object-contain rounded-lg">`;
            container.appendChild(slide);
        });

        document.getElementById('photoCurrentIdx').innerText = 1;
        document.getElementById('photoTotalCount').innerText = fotosAtuais.length;
        counter.classList.remove('hidden');

        if (fotosAtuais.length > 1) {
            btnPrev.classList.remove('hidden');
            btnNext.classList.remove('hidden');
        } else {
            btnPrev.classList.add('hidden');
            btnNext.classList.add('hidden');
        }

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
        if (stUpper === 'SOLICITADO') {
            badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-amber-900/40 text-amber-400 border-amber-700/50';
        } else if (stUpper === 'ENTREGUE') {
            badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-slate-800 text-slate-400 border-slate-700';
        } else if (stUpper === 'PARA DOAÇÃO' || stUpper === 'PARA DOACAO') {
            badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-purple-900/40 text-purple-400 border-purple-700/50';
        } else if (stUpper === 'DOAÇÃO FEITA' || stUpper === 'DOACAO FEITA') {
            badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-pink-900/40 text-pink-400 border-pink-700/50';
        } else {
            badgeStatus.className = 'text-[10px] font-bold px-2 py-0.5 rounded uppercase border bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
        }
    }

    if (stUpper !== 'DISPONÍVEL') {
        btnSolicitar.disabled = true;
        btnSolicitar.innerText = `ITEM EM STATUS: ${stUpper}`;
        btnSolicitar.className = "w-full bg-gray-700 text-gray-400 cursor-not-allowed font-bold py-3.5 rounded-xl text-sm uppercase border border-gray-600";
    } else {
        btnSolicitar.disabled = false;
        btnSolicitar.innerText = "ESTE É O MEU ITEM / SOLICITAR COLETA";
        btnSolicitar.className = "w-full dynamic-btn font-bold py-3.5 rounded-xl text-sm uppercase";
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
    
    // Animação de entrada
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);

    tituloEl.innerText = titulo;
    msgEl.innerText = mensagem;

    if (tipo === 'sucesso') {
        icone.innerHTML = '<i class="fas fa-check-circle text-green-500"></i>';
    } else if (tipo === 'erro') {
        icone.innerHTML = '<i class="fas fa-exclamation-circle text-red-500"></i>';
    } else {
        icone.innerHTML = '<i class="fas fa-info-circle text-blue-500"></i>';
    }
}

function fecharModalAviso() {
    const modal = document.getElementById('modalAviso');
    const content = document.getElementById('modalAvisoContent');

    // Animação de saída
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');

    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function abrirModalSolicitar() {
    if (!itemSelecionado) return;
    const stUpper = normalizarStatus(itemSelecionado.status);
    if (stUpper !== 'DISPONÍVEL') {
        mostrarAviso('Atenção', 'Este item não está mais disponível para solicitação.', 'erro');
        return;
    }

    const modal = document.getElementById('modalSolicitar');
    const content = document.getElementById('modalSolicitarContent');
    const errorMsg = document.getElementById('modalSolicitarError');
    
    // Limpa campos
    document.getElementById('inputNomeSolicitante').value = '';
    document.getElementById('inputRmSolicitante').value = '';
    errorMsg.classList.add('hidden');
    
    // Reseta estado do botão
    const btnConfirmar = document.getElementById('btnConfirmarSolicitacao');
    const btnText = document.getElementById('btnConfirmarText');
    const btnSpinner = document.getElementById('btnConfirmarSpinner');
    btnConfirmar.disabled = false;
    btnConfirmar.classList.remove('opacity-70', 'cursor-not-allowed');
    btnText.innerText = 'Confirmar Dados';
    btnSpinner.classList.add('hidden');

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

    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

async function confirmarSolicitacao() {
    const inputNome = document.getElementById('inputNomeSolicitante').value.trim();
    const inputRm = document.getElementById('inputRmSolicitante').value.trim();
    const errorMsg = document.getElementById('modalSolicitarError');
    const btnConfirmar = document.getElementById('btnConfirmarSolicitacao');
    const btnText = document.getElementById('btnConfirmarText');
    const btnSpinner = document.getElementById('btnConfirmarSpinner');

    if (!inputNome || !inputRm) {
        errorMsg.innerText = "Você precisa preencher seu Nome e RM!";
        errorMsg.classList.remove('hidden');
        return;
    }
    
    if (inputRm.length < 4) {
        errorMsg.innerText = "Digite um RM válido!";
        errorMsg.classList.remove('hidden');
        return;
    }

    errorMsg.classList.add('hidden');

    // UI DE CARREGAMENTO NO BOTÃO (Protege contra múltiplos cliques)
    btnConfirmar.disabled = true;
    btnConfirmar.classList.add('opacity-70', 'cursor-not-allowed');
    btnText.innerText = 'Enviando...';
    btnSpinner.classList.remove('hidden');

    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: itemSelecionado.id,
                nome: inputNome,
                rm: inputRm
            })
        });

        const res = await response.json();
        
        fecharModalSolicitar(); // Fecha o modal de formulário

        if (response.ok && res.success) {
            // Em vez do alert() feio, chama nosso modal bonito
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

window.onload = () => {
    carregarPreferenciasAparencia();
    carregarItensDaAPI();

    setTimeout(() => {
        const defaultBtn = document.querySelector('.cat-btn');
        if (defaultBtn) moveIndicator(defaultBtn);
    }, 100);
};

window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.cat-btn.text-white');
    if (activeBtn) moveIndicator(activeBtn);
});