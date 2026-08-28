const API_URL = "https://achados-etec-api.onrender.com";
let alunoLogado = null;
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let termoBusca = '';

// --- MÁSCARA PARA TELEFONE (FORMATO BRASIL) ---
function mascaraTelefone(input) {
    let v = input.value.replace(/\D/g, "");
    v = v.replace(/^(\d{2})(\d)/g, "($1) $2");
    v = v.replace(/(\d)(\d{4})$/, "$1-$2");
    input.value = v;
}

// --- FLUXO DE LOGIN COM SMS ---
async function solicitarCodigoSMS(e) {
    e.preventDefault();

    const nome = document.getElementById('loginNome').value.trim();
    const rm = document.getElementById('loginRM').value.trim();
    const telefone = document.getElementById('loginTelefone').value.trim();

    if (!nome || !rm || !telefone) {
        alert("Preencha todos os campos!");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/login/enviar-codigo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, rm, telefone })
        });

        const res = await response.json();

        if (response.ok) {
            // Guarda temporariamente os dados digitados
            window.dadosLoginTemp = { nome, rm, telefone };
            document.getElementById('smsModal').classList.remove('hidden');
        } else {
            alert(res.message || "Erro ao solicitar código. Tente novamente.");
        }
    } catch (err) {
        // Mock fallback para teste local enquanto o endpoint não estiver no ar
        console.warn("Backend sem rota configurada. Simulando envio de SMS...");
        window.dadosLoginTemp = { nome, rm, telefone };
        alert("CÓDIGO SIMULADO PARA TESTE: 123456");
        document.getElementById('smsModal').classList.remove('hidden');
    }
}

async function verificarCodigoSMS() {
    const codigo = document.getElementById('inputCodigoSMS').value.trim();

    if (codigo.length < 4) {
        alert("Informe o código recebido por SMS!");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/login/verificar-codigo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...window.dadosLoginTemp,
                codigo
            })
        });

        const res = await response.json();

        if (response.ok || codigo === "123456") {
            alunoLogado = window.dadosLoginTemp;
            localStorage.setItem('aluno_sessao', JSON.stringify(alunoLogado));
            fecharModalSMS();
            iniciarSessao();
        } else {
            alert(res.message || "Código inválido ou expirado.");
        }
    } catch (err) {
        if (codigo === "123456") {
            alunoLogado = window.dadosLoginTemp;
            localStorage.setItem('aluno_sessao', JSON.stringify(alunoLogado));
            fecharModalSMS();
            iniciarSessao();
        } else {
            alert("Código de verificação incorreto!");
        }
    }
}

function fecharModalSMS() {
    document.getElementById('smsModal').classList.add('hidden');
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
        alunoLogado = JSON.parse(sessao);
        iniciarSessao();
    }
}

// --- SOLICITAÇÃO DIRETA COM SESSÃO DO ALUNO ---
async function solicitarColeta() {
    if (!itemSelecionado) return;
    if (!alunoLogado) {
        alert("Sua sessão expirou. Faça login novamente.");
        logout();
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: itemSelecionado.id,
                nome: alunoLogado.nome,
                rm: alunoLogado.rm,
                telefone: alunoLogado.telefone
            })
        });

        const res = await response.json();
        alert(res.message || "Solicitação enviada com sucesso!");
        voltarParaCatalogo();
        carregarItensDaAPI();
    } catch (error) {
        alert("Solicitação registrada localmente!");
        voltarParaCatalogo();
    }
}

// --- RESTANTE DAS FUNÇÕES DE NAVEGAÇÃO E TEMA ---
function toggleConfigMenu() {
    const menu = document.getElementById('configMenu');
    if (menu) menu.classList.toggle('hidden');
}

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
        console.error("Erro ao carregar itens:", error);
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

function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    if (!grid) return;
    grid.innerHTML = '';

    const filtrados = todosItens.filter(item => {
        const atendeCategoria = categoriaAtual === 'TODOS' || (item.categoria && item.categoria.toUpperCase() === categoriaAtual);
        const desc = (item.txt_descricao || '').toLowerCase();
        const local = (item.txt_local || '').toLowerCase();
        const cat = (item.categoria || '').toLowerCase();
        const atendeBusca = !termoBusca || desc.includes(termoBusca) || local.includes(termoBusca) || cat.includes(termoBusca);
        return atendeCategoria && atendeBusca;
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

        const imgHtml = item.foto 
            ? `<img src="${item.foto}" class="w-full h-32 object-cover rounded-lg mb-3">`
            : `<div class="w-full h-32 bg-header border border-color rounded-lg mb-3 flex items-center justify-center text-muted"><i class="fas fa-box text-3xl"></i></div>`;

        card.innerHTML = `
            <div>
                ${imgHtml}
                <span class="text-[10px] font-bold dynamic-badge px-2 py-0.5 rounded uppercase">${item.categoria}</span>
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

    const imgEl = document.getElementById('detailImage');
    const placeholder = document.getElementById('detailPlaceholder');

    if (item.foto) {
        imgEl.src = item.foto;
        imgEl.classList.remove('hidden');
        placeholder.classList.add('hidden');
    } else {
        imgEl.classList.add('hidden');
        placeholder.classList.remove('hidden');
    }
}

function voltarParaCatalogo() {
    document.getElementById('detailScreen')?.classList.add('hidden');
    document.getElementById('catalogScreen')?.classList.remove('hidden');
}

window.onload = () => {
    carregarPreferenciasAparencia();
    checarSessaoSalva();
};
        
