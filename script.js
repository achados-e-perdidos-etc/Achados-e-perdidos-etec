const API_URL = "";
let alunoLogado = null;
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let termoBusca = '';
let fotosAtuais = [];
let fotoIndiceAtual = 0;

// --- FLUXO DE LOGIN COM RESEND ---
async function solicitarCodigoEmail(e) {
    e.preventDefault();

    const nome = document.getElementById('loginNome').value.trim();
    const rm = document.getElementById('loginRM').value.trim();
    const email = document.getElementById('loginEmail').value.trim();

    if (!nome || !rm || !email) {
        alert("Preencha todos os campos!");
        return;
    }

    const btn = document.getElementById('btnEnviarEmail');
    btn.disabled = true;
    btn.innerHTML = `<span>ENVIANDO...</span><i class="fas fa-spinner fa-spin"></i>`;

    try {
        const response = await fetch(`${API_URL}/api/login/enviar-codigo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, rm, email })
        });

        const res = await response.json();

        if (response.ok && res.success) {
            window.dadosLoginTemp = { nome, rm, email };
            document.getElementById('otpModal').classList.remove('hidden');
            alert(res.message);
        } else {
            alert(res.message || "Erro ao enviar e-mail. Verifique o endereço digitado.");
        }
    } catch (err) {
        alert("Erro de conexão ao solicitar código.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>ENVIAR CÓDIGO POR E-MAIL</span><i class="fas fa-envelope"></i>`;
    }
}

async function verificarCodigoOTP() {
    const codigo = document.getElementById('inputCodigoOTP').value.trim();

    if (codigo.length < 6) {
        alert("Digite o código de 6 dígitos enviado ao seu e-mail!");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/login/verificar-codigo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: window.dadosLoginTemp.email,
                codigo
            })
        });

        const res = await response.json();

        if (response.ok && res.success) {
            alunoLogado = res.usuario;
            localStorage.setItem('aluno_sessao', JSON.stringify(alunoLogado));
            fecharModalOTP();
            iniciarSessao();
        } else {
            alert(res.message || "Código inválido ou expirado.");
        }
    } catch (err) {
        alert("Erro ao validar código.");
    }
}

function fecharModalOTP() {
    document.getElementById('otpModal').classList.add('hidden');
}

function iniciarSessao() {
    if (!alunoLogado) return;

    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('catalogScreen').classList.remove('hidden');

    const userInfo = document.getElementById('userInfo');
    const userName = document.getElementById('userName');
    const userRM = document.getElementById('userRM');

    if (userInfo && userName && userRM) {
        userName.innerText = alunoLogado.nome;
        userRM.innerText = `RM: ${alunoLogado.rm}`;
        userInfo.classList.remove('hidden');
    }

    carregarItensDaAPI();
}

function logout() {
    alunoLogado = null;
    localStorage.removeItem('aluno_sessao');
    document.getElementById('userInfo')?.classList.add('hidden');
    document.getElementById('catalogScreen')?.classList.add('hidden');
    document.getElementById('detailScreen')?.classList.add('hidden');
    document.getElementById('loginScreen')?.classList.remove('hidden');
}

function checarSessaoSalva() {
    const sessao = localStorage.getItem('aluno_sessao');
    if (sessao) {
        try {
            alunoLogado = JSON.parse(sessao);
            iniciarSessao();
        } catch (e) {
            localStorage.removeItem('aluno_sessao');
        }
    }
}

// --- SOLICITAÇÃO DIRETA COM DADOS DO ALUNO LOGADO ---
async function solicitarColeta() {
    if (!itemSelecionado) return;
    if (!alunoLogado) {
        alert("Sua sessão expirou. Faça login novamente.");
        logout();
        return;
    }

    const stUpper = normalizarStatus(itemSelecionado.status);
    if (stUpper !== 'DISPONÍVEL') {
        alert("Este item não está mais disponível para solicitação!");
        return;
    }

    if (!confirm(`Deseja confirmar a solicitação do item "${itemSelecionado.txt_descricao}" em nome de ${alunoLogado.nome} (RM: ${alunoLogado.rm})?`)) {
        return;
    }

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

// --- CONFIGURAÇÕES DE APARÊNCIA E NAVEGAÇÃO ---
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

window.onload = () => {
    carregarPreferenciasAparencia();
    checarSessaoSalva();
};
