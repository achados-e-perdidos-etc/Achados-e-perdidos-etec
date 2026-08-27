const API_URL = "https://achados-etec-api.onrender.com";
let alunoLogado = null;
let todosItens = [];
let itemSelecionado = null;
let categoriaAtual = 'TODOS';

// --- SISTEMA DE MENU DE CONFIGURAÇÕES ---
function toggleConfigMenu() {
    const menu = document.getElementById('configMenu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

// Fecha o menu de configurações se clicar fora dele
window.addEventListener('click', function(e) {
    const menu = document.getElementById('configMenu');
    if (!menu) return;
    
    const btn = e.target.closest('button');
    if (!menu.contains(e.target) && (!btn || !btn.getAttribute('onclick')?.includes('toggleConfigMenu'))) {
        menu.classList.add('hidden');
    }
});

// --- SISTEMA DE TEMA (CLARO / ESCURO) ---
function alternarModoEscuroClaro() {
    const isDark = document.body.classList.contains('dark-theme');
    const label = document.getElementById('themeLabel');
    const icon = document.getElementById('themeIcon');

    if (isDark) {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        if (label) label.innerText = "Modo Claro";
        if (icon) icon.className = "fas fa-sun text-yellow-500";
        localStorage.setItem('theme_mode', 'light');
    } else {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        if (label) label.innerText = "Modo Escuro";
        if (icon) icon.className = "fas fa-moon text-yellow-400";
        localStorage.setItem('theme_mode', 'dark');
    }
}

// --- SISTEMA DE CORES E LOGO DINÂMICA ---
const temasCores = {
    vermelho: {
        primary: '#dc2626',
        hover: '#b91c1c',
        text: '#f87171',
        subtle: '#450a0a',
        border: '#991b1b',
        logo: 'logo-vermelho.png'
    },
    verde: {
        primary: '#238636',
        hover: '#2ea043',
        text: '#4ade80',
        subtle: '#052e16',
        border: '#14532d',
        logo: 'logo-verde.png'
    },
    azul: {
        primary: '#0284c7',
        hover: '#0369a1',
        text: '#38bdf8',
        subtle: '#0c4a6e',
        border: '#0369a1',
        logo: 'logo-azul.png'
    },
    roxo: {
        primary: '#9333ea',
        hover: '#7e22ce',
        text: '#c084fc',
        subtle: '#3b0764',
        border: '#6b21a8',
        logo: 'logo-roxo.png'
    }
};

function mudarEstiloCor(cor) {
    const tema = temasCores[cor] || temasCores.vermelho;
    const root = document.documentElement;

    root.style.setProperty('--primary-color', tema.primary);
    root.style.setProperty('--primary-hover', tema.hover);
    root.style.setProperty('--primary-text', tema.text);
    root.style.setProperty('--primary-bg-subtle', tema.subtle);
    root.style.setProperty('--primary-border', tema.border);

    // Troca a logo dinamicamente sem quebrar a imagem
    const logoImg = document.getElementById('siteLogo');
    if (logoImg) {
        logoImg.src = tema.logo;
    }

    // Atualiza os marcadores no menu de configurações
    document.querySelectorAll('#configMenu i[id^="check-"]').forEach(el => el.classList.add('hidden'));
    const check = document.getElementById(`check-${cor}`);
    if (check) check.classList.remove('hidden');

    localStorage.setItem('theme_color', cor);
}

function carregarPreferenciasAparencia() {
    // Carrega o modo (Escuro / Claro)
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

    // Carrega a cor do tema e a logo correspondente
    const corSalva = localStorage.getItem('theme_color') || 'vermelho';
    mudarEstiloCor(corSalva);
}

// --- CONEXÃO COM A API ---
async function carregarItensDaAPI() {
    try {
        const response = await fetch(`${API_URL}/api/itens`);
        if (response.ok) {
            todosItens = await response.json();
            renderizarItens();
        }
    } catch (error) {
        console.error("Erro ao carregar dados da API:", error);
    }
}

function logout() {
    alunoLogado = null;
    document.getElementById('userInfo')?.classList.add('hidden');
    document.getElementById('catalogScreen')?.classList.add('hidden');
    document.getElementById('detailScreen')?.classList.add('hidden');
}

// --- CATEGORIAS E INDICADOR DESLIZANTE ---
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

    const filtrados = categoriaAtual === 'TODOS' 
        ? todosItens 
        : todosItens.filter(i => i.categoria && i.categoria.toUpperCase() === categoriaAtual);

    if (filtrados.length === 0) {
        grid.innerHTML = '<div class="col-span-2 text-center text-muted py-8">Nenhum objeto cadastrado nesta categoria.</div>';
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

// --- TELA DE DETALHES E SOLICITAÇÃO ---
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

async function solicitarColeta() {
    if (!itemSelecionado) return;

    let nomeDigitado = prompt("Por favor, digite seu Nome completo:");
    let rmDigitado = prompt("Por favor, digite seu RM:");

    if (!nomeDigitado || !rmDigitado) {
        alert("Você precisa informar seu Nome e RM para solicitar o item!");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/solicitar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: itemSelecionado.id,
                nome: nomeDigitado,
                rm: rmDigitado
            })
        });

        const res = await response.json();
        alert(res.message);
        voltarParaCatalogo();
        carregarItensDaAPI();
    } catch (error) {
        alert("Erro ao enviar a solicitação ao servidor.");
    }
}

// --- INICIALIZAÇÃO DA PÁGINA ---
window.onload = () => {
    carregarPreferenciasAparencia();
    carregarItensDaAPI();

    setTimeout(() => {
        const defaultBtn = document.querySelector('.cat-btn');
        if (defaultBtn) {
            moveIndicator(defaultBtn);
        }
    }, 100);
};

window.addEventListener('resize', () => {
    const activeBtn = document.querySelector('.cat-btn.text-white');
    if (activeBtn) moveIndicator(activeBtn);
});
