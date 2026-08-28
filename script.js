const API_URL = "https://achados-etec-api.onrender.com";
let alunoLogado = null;
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';
let statusAtual = 'TODOS';
let termoBusca = '';

// --- INICIALIZAÇÃO ---
document.addEventListener("DOMContentLoaded", () => {
    carregarItens();
    
    // Seleciona o primeiro botão ("TODOS") como ativo inicialmente
    const btnTodos = document.querySelector('.cat-btn');
    if (btnTodos) {
        atualizarPillSlide(btnTodos);
    }
});

// --- REQUISIÇÃO À API ---
async function carregarItens() {
    try {
        const response = await fetch(`${API_URL}/itens`);
        if (!response.ok) throw new Error("Erro ao buscar dados do servidor");
        
        todosItens = await response.json();
        renderizarItens();
    } catch (erro) {
        console.error("Erro no carregamento:", erro);
        const grid = document.getElementById('itemsGrid');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center text-accent py-12 bg-card border border-color rounded-xl">
                    <i class="fas fa-exclamation-triangle text-3xl mb-2"></i>
                    <p class="text-sm font-semibold">Falha ao conectar à API.</p>
                    <p class="text-xs text-muted mt-1">Verifique sua conexão ou tente novamente mais tarde.</p>
                </div>
            `;
        }
    }
}

// --- FILTROS DE INTERFACE ---
function filtrarCategoria(categoria, elemento) {
    categoriaAtual = categoria;
    atualizarPillSlide(elemento);
    renderizarItens();
}

function filtrarStatus(status) {
    statusAtual = status;
    renderizarItens();
}

function filtrarBusca(termo) {
    termoBusca = termo.toLowerCase().trim();
    renderizarItens();
}

// --- EFEITO VISUAL DO SLIDER DE CATEGORIA ---
function atualizarPillSlide(elemento) {
    const indicator = document.getElementById('catIndicator');
    const botoes = document.querySelectorAll('.cat-btn');

    botoes.forEach(btn => {
        btn.classList.remove('text-white');
        btn.classList.add('text-muted');
    });

    if (elemento && indicator) {
        elemento.classList.remove('text-muted');
        elemento.classList.add('text-white');

        indicator.style.width = `${elemento.offsetWidth}px`;
        indicator.style.height = `${elemento.offsetHeight}px`;
        indicator.style.left = `${elemento.offsetLeft}px`;
        indicator.style.top = `${elemento.offsetTop}px`;
        indicator.style.opacity = '1';
    }
}

// --- RENDERIZAÇÃO DA LISTA ---
function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    if (!grid) return;

    grid.innerHTML = '';

    const filtrados = todosItens.filter(item => {
        // 1. Filtro por Categoria
        const atendeCategoria = categoriaAtual === 'TODOS' || 
            (item.categoria && item.categoria.toUpperCase() === categoriaAtual);

        // 2. Filtro por Status (Suporta tanto GUARDADO quanto DISPONÍVEL)
        const itemStatus = (item.status || 'GUARDADO').toUpperCase();
        const atendeStatus = statusAtual === 'TODOS' || 
            (statusAtual === 'GUARDADO' && (itemStatus === 'GUARDADO' || itemStatus === 'DISPONÍVEL')) ||
            (itemStatus === statusAtual);

        // 3. Filtro por Busca de Texto
        const desc = (item.txt_descricao || '').toLowerCase();
        const local = (item.txt_local || '').toLowerCase();
        const cat = (item.categoria || '').toLowerCase();
        
        const atendeBusca = !termoBusca || 
            desc.includes(termoBusca) || 
            local.includes(termoBusca) || 
            cat.includes(termoBusca);

        return atendeCategoria && atendeStatus && atendeBusca;
    });

    // Estado vazio caso a busca não retorne itens
    if (filtrados.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center text-muted py-12 bg-card border border-color rounded-xl">
                <i class="fas fa-search text-3xl mb-2 text-muted"></i>
                <p class="text-sm font-semibold">Nenhum objeto encontrado.</p>
                <p class="text-xs text-muted mt-1">Tente ajustar a categoria, a busca ou o status selecionado.</p>
            </div>
        `;
        return;
    }

    // Renderização dos cards
    filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = "bg-card border border-color rounded-xl p-4 flex flex-col justify-between hover:border-accent transition duration-200 cursor-pointer shadow-sm hover:shadow-md";

        const imgHtml = item.foto 
            ? `<img src="${item.foto}" alt="${item.txt_descricao}" class="w-full h-36 object-cover rounded-lg mb-3">`
            : `<div class="w-full h-36 bg-header border border-color rounded-lg mb-3 flex items-center justify-center text-muted"><i class="fas fa-box-open text-3xl"></i></div>`;

        // Definição de estilo das badges de Status
        const statusUpper = (item.status || 'GUARDADO').toUpperCase();
        let statusBadgeColor = 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
        
        if (statusUpper === 'SOLICITADO') {
            statusBadgeColor = 'bg-amber-900/40 text-amber-400 border-amber-700/50';
        } else if (statusUpper === 'ENTREGUE') {
            statusBadgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
        }

        card.innerHTML = `
            <div>
                ${imgHtml}
                <div class="flex justify-between items-center mb-1 gap-2">
                    <span class="text-[10px] font-bold bg-header border border-color text-main px-2 py-0.5 rounded uppercase tracking-wider">${item.categoria || 'GERAL'}</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${statusBadgeColor}">${statusUpper}</span>
                </div>
                <h4 class="font-bold text-sm mt-2 text-white line-clamp-1">${item.txt_descricao}</h4>
                <p class="text-xs text-muted mt-1"><i class="fas fa-map-marker-alt text-accent mr-1"></i> ${item.txt_local}</p>
            </div>
        `;
        grid.appendChild(card);
    });
}
