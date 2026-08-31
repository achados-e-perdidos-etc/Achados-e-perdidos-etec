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

// ------------------------------------------------------------------
// SISTEMA DE LOGIN INSTITUCIONAL (ATUALIZADO)
// ------------------------------------------------------------------
function verificarSessao() {
    const userStr = localStorage.getItem('aluno_etec_sessao');
    if (userStr) {
        alunoLogado = JSON.parse(userStr);
        
        // Esconde Login, Mostra Catálogo
        document.getElementById('loginScreen').classList.add('hidden');
        document.getElementById('catalogScreen').classList.remove('hidden');
        document.getElementById('userInfo').classList.remove('hidden');
        
        // Atualiza cabeçalho
        document.getElementById('userName').innerText = alunoLogado.nome;
        document.getElementById('userRM').innerText = "RM: " + alunoLogado.rm;
        
        // Carrega dados da API apenas se estiver logado
        carregarItensDaAPI();
    } else {
        // Exige Login
        document.getElementById('loginScreen').classList.remove('hidden');
        document.getElementById('catalogScreen').classList.add('hidden');
        document.getElementById('detailScreen').classList.add('hidden');
        document.getElementById('userInfo').classList.add('hidden');
    }
}

function fazerLogin(event) {
    event.preventDefault(); // Impede a página de recarregar
    
    const nome = document.getElementById('loginNome').value.trim();
    const rm = document.getElementById('loginRM').value.trim();
    const email = document.getElementById('loginEmail').value.trim().toLowerCase();

    // Validação obrigatória do NOVO domínio do Centro Paula Souza
    if (!email.endsWith('@aluno.cps.sp.gov.br')) {
        alert("🔒 Acesso Bloqueado!\n\nVocê precisa usar o seu e-mail institucional oficial (terminado em @aluno.cps.sp.gov.br) para acessar o sistema.");
        return;
    }

    // Salva a sessão no navegador do aluno
    alunoLogado = { nome, rm, email };
    localStorage.setItem('aluno_etec_sessao', JSON.stringify(alunoLogado));
    
    verificarSessao();
}

function logout() {
    if(confirm("Tem certeza que deseja sair da sua conta?")) {
        alunoLogado = null;
        localStorage.removeItem('aluno_etec_sessao');
        verificarSessao(); // Volta para a tela de login
        
        // Limpa os campos do formulário para o próximo login
        document.getElementById('loginForm').reset();
    }
}
// ------------------------------------------------------------------

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
        btnSolicitar.innerHTML = `<i class="fas fa-lock"></i> ITEM EM STATUS: ${stUpper}`;
        btnSolicitar.className = "w-full flex justify-center items-center gap-2 bg-gray-700 text-gray-400 cursor-not-allowed font-bold py-3.5 rounded-xl text-sm uppercase border border-gray-600";
    } else {
        btnSolicitar.disabled = false;
        btnSolicitar.innerHTML = `<i class="fas fa-hand-paper"></i> ESTE É O MEU ITEM / SOLICITAR COLETA`;
        btnSolicitar.className = "w-full flex justify-center items-center gap-2 dynamic-btn font-bold py-3.5 rounded-xl text-sm uppercase";
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

async function solicitarColeta() {
    if (!itemSelecionado) return;
    
    // Verificação de segurança extra para garantir que o aluno logou
    if (!alunoLogado) {
        alert("Você precisa estar logado para solicitar um item!");
        return;
    }

    const stUpper = normalizarStatus(itemSelecionado.status);
    if (stUpper !== 'DISPONÍVEL') {
        alert("Este item não está mais disponível para solicitação!");
        return;
    }

    // Pergunta se ele confirma solicitar no nome dele (dados pegos no login)
    const confirmacao = confirm(`Você está solicitando este item como:\n\nNome: ${alunoLogado.nome}\nRM: ${alunoLogado.rm}\n\nDeseja confirmar a solicitação?`);
    
    if (!confirmacao) return;

    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // Enviamos o email também caso o backend queira mandar a notificação direta!
            body: JSON.stringify({
                id: itemSelecionado.id,
                nome: alunoLogado.nome,
                rm: alunoLogado.rm,
                email: alunoLogado.email
            })
        });

        const res = await response.json();
        
        if (response.ok && res.success) {
            alert(res.message);
            voltarParaCatalogo();
            carregarItensDaAPI();
        } else {
            alert(res.message || "Não foi possível realizar a solicitação.");
        }
    } catch (error) {
        alert("Erro ao enviar a solicitação ao servidor.");
    }
}

window.onload = () => {
    carregarPreferenciasAparencia();
    verificarSessao(); // Inicia verificando se há login, se houver ele carrega a API.

    setTimeout(() => {
        const defaultBtn = document.querySelector('.cat-btn');
        if (defaultBtn) moveIndicator(defaultBtn);
    }, 100);
};

window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.cat-btn.text-white');
    if (activeBtn) moveIndicator(activeBtn);
});
