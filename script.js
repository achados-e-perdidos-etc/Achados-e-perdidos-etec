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
// NOVO: COMPRESSOR INTELIGENTE DE FOTOS NO NAVEGADOR (HTML5 CANVAS)
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
            // Formato ISO: YYYY-MM-DD
            ano = parseInt(partes[0], 10);
            mes = parseInt(partes[1], 10) - 1;
            dia = parseInt(partes[2], 10);
        } else {
            // Formato Brasileiro: DD/MM/YYYY
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

function normalizarStatus(itemOuStatus, dataItem = null) {
    let st = '';
    let dataStr = dataItem;
    if (typeof itemOuStatus === 'object' && itemOuStatus !== null) {
        st = (itemOuStatus.status || 'DISPONÍVEL').toUpperCase().trim();
        dataStr = itemOuStatus.data_encontrado || itemOuStatus.txt_data;
    } else {
        st = (itemOuStatus || 'DISPONÍVEL').toUpperCase().trim();
    }

    // Se já estiver explicitamente como doação no banco de dados
    if (st.includes('DOAÇÃO') || st.includes('DOACAO')) {
        return 'PARA DOAÇÃO';
    }
    if (st === 'ENTREGUE' || st === 'SOLICITADO') {
        return st;
    }

    // Se estiver DISPONÍVEL, só converte para DOAÇÃO se realmente tiver mais de 90 dias
    if (st === 'DISPONÍVEL' && dataStr) {
        const dias = calcularDiasPassados(dataStr);
        if (dias >= 90) {
            return 'PARA DOAÇÃO';
        }
    }
    return st;
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
        document.getElementById('loginAlunoScreen').classList.add('hidden');
        document.getElementById('lblBemVindo').innerText = `Olá, ${alunoSessao.nome.split(' ')[0]}!`;
        
        document.getElementById('perfilNomeCompleto').innerText = alunoSessao.nome;
        document.getElementById('perfilEmailInstitucional').innerText = alunoSessao.email;
        document.getElementById('perfilRM').innerText = alunoSessao.rm || 'N/A';

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
    const btn = document.getElementById('btnAcessoLogin');
    btn.innerText = "Entrando..."; btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/auth/login-aluno`, {
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
    if (!email.endsWith('@aluno.cps.sp.gov.br')) return mostrarToast("Use um e-mail @aluno.cps.sp.gov.br", "error");
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
                    listaRel.innerHTML += `
                        <div class="glass-panel rounded-2xl p-4 flex justify-between items-center gap-3 border border-white/5">
                            <div>
                                <p class="text-xs font-bold text-white"><span class="text-amber-400">[${r.categoria}]</span> ${r.descricao}</p>
                                <p class="text-[10px] text-slate-400 mt-0.5">Data do registro: ${r.data || 'Recente'}</p>
                            </div>
                            <span class="text-[10px] font-black px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wider">ATIVO</span>
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
    if (st !== 'DISPONÍVEL') { 
        b.disabled = true; 
        b.innerText = `STATUS: ${st}`; 
        b.className = "w-full bg-slate-800 text-slate-500 font-bold py-3.5 rounded-xl text-xs uppercase cursor-not-allowed"; 
    } else { 
        b.disabled = false; 
        b.innerText = "ESTE É O MEU ITEM"; 
        b.className = "w-full bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-extrabold py-3.5 rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-red-600/30 transition transform active:scale-[0.98]"; 
    }
}

function voltarParaCatalogo() { mudarAba('catalogo'); }

function navegarFotos(dir) { 
    const c = document.getElementById('carouselContainer'); 
    if(fotosAtuais.length > 1) { 
        fotoIndiceAtual = (fotoIndiceAtual + dir + fotosAtuais.length) % fotosAtuais.length; 
        c.scrollTo({ left: c.clientWidth * fotoIndiceAtual, behavior: 'smooth' }); 
        document.getElementById('photoCurrentIdx').innerText = fotoIndiceAtual + 1;
    } 
}

function abrirNovoModal() { 
    if(itemSelecionado) document.getElementById('modalNovo').classList.remove('hidden'); 
}

async function enviarNovo() {
    const btn = document.getElementById('btnNovo'); 
    btn.disabled = true; btn.innerText = "Processando...";
    try {
        const token = localStorage.getItem('aluno_token');
        const res = await fetch(`${API_URL}/api/solicitar`, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            }, 
            body: JSON.stringify({ 
                id: itemSelecionado.id, 
                nome: alunoSessao.nome, 
                rm: alunoSessao.rm, 
                email: alunoSessao.email 
            }) 
        });
        const data = await res.json();
        if(res.ok && data.success) { 
            mostrarToast("Solicitação realizada! Compareça à secretaria para retirar.", "success"); 
            document.getElementById('modalNovo').classList.add('hidden'); 
            voltarParaCatalogo(); 
            carregarItensDaAPI(); 
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro na solicitação.", "error"); }
    btn.disabled = false; btn.innerText = "Sim, é meu!";
}

async function enviarAvisoMural(e) {
    e.preventDefault();
    const btn = document.getElementById('btnPublicarMural'); 
    btn.disabled = true;
    try {
        const token = localStorage.getItem('aluno_token');
        const res = await fetch(`${API_URL}/api/mural`, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            }, 
            body: JSON.stringify({ 
                nome: alunoSessao.nome, 
                rm: alunoSessao.rm, 
                email: alunoSessao.email, 
                categoria: document.getElementById('muralCategoria').value, 
                descricao: document.getElementById('muralDescricao').value.trim() 
            }) 
        });
        const data = await res.json();
        if (res.ok && data.success) { 
            document.getElementById('muralDescricao').value = ''; 
            if (data.matches_encontrados && data.matches_encontrados.length > 0) { 
                dispararNotificacaoNativa("Objeto Parecido Encontrado!", "O sistema achou algo parecido com o que você perdeu!");
                exibirMatchesImediatos(data.matches_encontrados); 
            } else {
                mostrarToast("Relato publicado com sucesso no mural!", "success"); 
            }
            carregarMuralPublico();
        } else mostrarToast(data.message || "Erro ao publicar.", "error");
    } catch { mostrarToast("Erro ao conectar.", "error"); }
    btn.disabled = false;
}

async function carregarMuralPublico() {
    const container = document.getElementById('listaMuralPublico');
    if (!container) return;
    try {
        const res = await fetch(`${API_URL}/api/mural`);
        if (res.ok) {
            const mural = await res.json();
            if (mural.length === 0) {
                container.innerHTML = `<p class="text-xs text-slate-500 italic p-4 text-center glass-panel rounded-2xl">Nenhum relato recente publicado.</p>`;
                return;
            }
            container.innerHTML = mural.map(m => `
                <div class="glass-panel rounded-2xl p-4 border border-white/5 space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">${m.categoria}</span>
                        <span class="text-[10px] text-slate-500">${m.data_registro || ''}</span>
                    </div>
                    <p class="text-xs text-slate-200 font-medium">"${m.descricao}"</p>
                    <p class="text-[10px] text-slate-400 font-bold"><i class="fas fa-user text-slate-500 mr-1"></i>${m.nome_aluno}</p>
                </div>
            `).join('');
        }
    } catch(e){}
}

function exibirMatchesImediatos(itens) {
    const lst = document.getElementById('matchItensLista'); 
    lst.innerHTML = '';
    itens.forEach(i => {
        lst.innerHTML += `
            <div class="glass-panel p-3 rounded-2xl flex justify-between items-center gap-3 border border-white/5">
                <div>
                    <p class="text-xs font-bold text-white">${i.nome || i.txt_descricao}</p>
                    <span class="text-[9px] uppercase font-bold text-emerald-400">${i.categoria}</span>
                </div>
                <button onclick='abrirDetalhes(${JSON.stringify(i).replace(/'/g, "&apos;")}); document.getElementById("modalMatchImediato").classList.add("hidden");' class="px-3 py-1.5 rounded-xl bg-red-600 text-white font-bold text-xs">VER</button>
            </div>`;
    });
    document.getElementById('modalMatchImediato').classList.remove('hidden');
}

function alternarJanelaChat() {
    chatAberto = !chatAberto;
    document.getElementById('janelaChat').classList.toggle('hidden', !chatAberto);
    document.getElementById('badgeChatWeb').classList.add('hidden');
    if (chatAberto) { 
        atualizarMensagensChat(); 
        iniciarPollingChatAluno();
    } else {
        pararPollingChatAluno();
    }
}

function iniciarPollingChatAluno() {
    pararPollingChatAluno();
    chatTimerPolling = setInterval(() => {
        if (!document.hidden && chatAberto) {
            atualizarMensagensChat();
        }
    }, 3000);
}

function pararPollingChatAluno() {
    if (chatTimerPolling) {
        clearInterval(chatTimerPolling);
        chatTimerPolling = null;
    }
}

document.addEventListener('visibilitychange', () => {
    if (!document.hidden && chatAberto) {
        atualizarMensagensChat();
    }
});

function abrirChatComItem() { 
    if(!chatAberto) alternarJanelaChat(); 
    if(itemSelecionado) {
        document.getElementById('chatInputTexto').value = `Olá! Gostaria de informações sobre o item #${itemSelecionado.id} (${itemSelecionado.nome || itemSelecionado.txt_descricao}): `;
        document.getElementById('chatInputTexto').focus();
    } 
}

async function atualizarMensagensChat() {
    if(!alunoSessao) return;
    try {
        const res = await fetch(`${API_URL}/api/chat/mensagens/${alunoSessao.rm}?marcar_lida=true&origem=ALUNO`);
        if(!res.ok) return;
        const msgs = await res.json();
        const c = document.getElementById('chatMensagens');
        if(msgs.length !== ultimaQtdMensagens) {
            if (ultimaQtdMensagens > 0) {
                const ultimaMensagem = msgs[msgs.length - 1];
                if (ultimaMensagem.remetente !== 'ALUNO') {
                    tocarSomNotificacao();
                    if (document.hidden || !chatAberto) {
                        dispararNotificacaoNativa("Secretaria ETEC respondeu", ultimaMensagem.mensagem);
                    }
                }
            }
            ultimaQtdMensagens = msgs.length; 
            c.innerHTML = '';
            msgs.forEach(m => { 
                const eu = m.remetente === 'ALUNO'; 
                c.innerHTML += `
                    <div class="flex w-full ${eu ? 'justify-end' : 'justify-start'}">
                        <div class="flex items-end gap-2 max-w-[85%] ${eu ? 'flex-row-reverse' : 'flex-row'}">
                            ${!eu ? `<div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-red-600 to-rose-600 shadow-md text-white"><i class="fas fa-shield-alt text-[10px]"></i></div>` : ''}
                            <div class="rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-sm ${eu ? 'rounded-tr-sm bg-gradient-to-r from-red-600 to-rose-600 text-white' : 'rounded-tl-sm border border-white/10 bg-[#161c28] text-slate-200'}">
                                ${m.mensagem}
                            </div>
                        </div>
                    </div>`; 
            });
            c.scrollTop = c.scrollHeight;
        }
    } catch(e){}
}

async function enviarMensagemChat(e) {
    e.preventDefault();
    const txt = document.getElementById('chatInputTexto').value.trim();
    if(!txt || !alunoSessao) return;
    try {
        const res = await fetch(`${API_URL}/api/chat/enviar`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ rm: alunoSessao.rm, nome: alunoSessao.nome, remetente: 'ALUNO', mensagem: txt }) 
        });
        if(res.ok) {
            document.getElementById('chatInputTexto').value = ''; 
            atualizarMensagensChat();
        }
    } catch(e){}
}

function abrirModalCadastrarAluno() {
    fotosAlunoSelecionadas = [];
    renderizarGridPreviewAluno();
    const badge = document.getElementById('statusCompressaoFotos');
    if (badge) badge.classList.add('hidden');
    document.getElementById('modalCadastrarAluno').classList.remove('hidden');
}

// ATUALIZADO: COMPRESSÃO AUTOMÁTICA DE IMAGENS DO CELULAR
async function prepararFotosAluno(input) {
    if (input.files && input.files.length > 0) {
        const badge = document.getElementById('statusCompressaoFotos');
        if (badge) {
            badge.innerText = "Comprimindo fotos...";
            badge.className = "text-[10px] text-amber-400 font-bold";
            badge.classList.remove('hidden');
        }

        const arquivos = Array.from(input.files).slice(0, 4 - fotosAlunoSelecionadas.length);
        for (const file of arquivos) {
            try {
                // Comprime a foto para no máximo 1200px e qualidade 75%
                const fotoComprimida = await comprimirImagem(file, 1200, 0.75);
                if (fotosAlunoSelecionadas.length < 4) {
                    fotosAlunoSelecionadas.push(fotoComprimida);
                }
            } catch (err) {
                console.warn("Erro ao comprimir, usando original:", err);
            }
        }

        renderizarGridPreviewAluno();
        input.value = '';

        if (badge) {
            badge.innerText = "✓ Fotos otimizadas";
            badge.className = "text-[10px] text-emerald-400 font-bold";
        }
    }
}

function renderizarGridPreviewAluno() {
    const container = document.getElementById('gridPreviewAluno');
    container.innerHTML = '';
    if (fotosAlunoSelecionadas.length > 0) {
        container.classList.remove('hidden');
        fotosAlunoSelecionadas.forEach((f, i) => {
            container.innerHTML += `
                <div class="relative w-20 h-20 shrink-0">
                    <img src="${f}" class="w-full h-full object-cover rounded-xl border border-white/10">
                    <button type="button" onclick="fotosAlunoSelecionadas.splice(${i}, 1); renderizarGridPreviewAluno();" class="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-[10px]"><i class="fas fa-times"></i></button>
                </div>`;
        });
    } else container.classList.add('hidden');
}

async function enviarCadastroAluno(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarAlunoItem');
    btn.innerText = "Enviando..."; btn.disabled = true;

    const payload = {
        nome: document.getElementById('alunoItemNome').value.trim(),
        descricao: document.getElementById('alunoItemDesc').value.trim(),
        categoria: document.getElementById('alunoItemCat').value,
        local: document.getElementById('alunoItemLocal').value.trim(),
        data: new Date().toLocaleDateString('pt-BR'),
        rm: alunoSessao.rm,
        fotos: fotosAlunoSelecionadas,
        foto: fotosAlunoSelecionadas[0] || ""
    };

    try {
        const token = localStorage.getItem('aluno_token');
        const res = await fetch(`${API_URL}/api/itens/cadastrar-aluno`, {
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast("Objeto enviado para moderação da secretaria!", "success");
            document.getElementById('modalCadastrarAluno').classList.add('hidden');
            e.target.reset();
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro ao conectar.", "error"); }
    btn.innerText = "Enviar para Moderação da Secretaria"; btn.disabled = false;
}

window.onload = () => { 
    document.body.classList.add('dark-theme'); 
    const splash = document.getElementById('splashScreenAnimacao');
    const video = document.getElementById('videoSplash');
    if (splash && video) {
        video.muted = true;
        video.play().catch(() => {});
        const encerrarSplash = () => {
            splash.classList.add('opacity-0');
            setTimeout(() => { 
                splash.classList.add('hidden'); 
                splash.style.display = 'none'; 
                checarSessao(); 
            }, 700);
        };
        video.onended = encerrarSplash;
        setTimeout(() => { if (!splash.classList.contains('hidden')) encerrarSplash(); }, 9000); 
    } else checarSessao();
};
