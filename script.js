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

// --- SISTEMA DE NOTIFICAÇÕES (PUSH) ---
function solicitarPermissaoNotificacao() {
    if ("Notification" in window) {
        if (Notification.permission === "granted") {
            mostrarToast("As notificações já estão ativadas!", "success");
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    mostrarToast("Notificações ativadas com sucesso!", "success");
                }
            });
        } else {
            mostrarToast("Permissão negada. Ative nas configurações do navegador.", "error");
        }
    } else {
        mostrarToast("Seu navegador não suporta notificações nativas.", "error");
    }
}

function dispararNotificacaoNativa(titulo, corpo) {
    if ("Notification" in window && Notification.permission === "granted") {
        const notificacao = new Notification(titulo, {
            body: corpo,
            icon: "logo.png"
        });
        notificacao.onclick = function() {
            window.focus();
            this.close();
        };
    }
}

// --- SISTEMA DE AUTENTICAÇÃO ---
function checarSessao() {
    const token = localStorage.getItem('aluno_token');
    const dados = localStorage.getItem('aluno_dados');
    if (token && dados) {
        alunoSessao = JSON.parse(dados);
        document.getElementById('loginAlunoScreen').classList.add('hidden');
        document.getElementById('lblBemVindo').innerText = `Bem-vindo(a), ${alunoSessao.nome.split(' ')[0]}!`;
        carregarItensDaAPI();
        carregarCategoriasDinamicamente();
        
        if ("Notification" in window && Notification.permission === "default") {
            setTimeout(solicitarPermissaoNotificacao, 3000);
        }
    } else {
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
    }
}

function fazerLogoff() {
    localStorage.removeItem('aluno_token');
    localStorage.removeItem('aluno_dados');
    window.location.reload();
}

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
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: document.getElementById('loginEmailAluno').value, senha: document.getElementById('loginSenhaAluno').value })
        });
        const data = await res.json();
        if (data.success) {
            localStorage.setItem('aluno_token', data.token);
            localStorage.setItem('aluno_dados', JSON.stringify(data.aluno));
            checarSessao();
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro de conexão.", "error"); }
    btn.innerText = "Entrar"; btn.disabled = false;
}

async function enviarCodigoAuth(idEmail, idBtn, idShow, idHide) {
    const email = document.getElementById(idEmail).value.trim();
    if (!email.endswith('@aluno.cps.sp.gov.br')) return mostrarToast("Use um e-mail @aluno.cps.sp.gov.br", "error");
    const btn = document.getElementById(idBtn);
    btn.innerText = "Enviando..."; btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/auth/enviar-codigo`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
        const data = await res.json();
        if (data.success) { document.getElementById(idShow).classList.remove('hidden'); document.getElementById(idHide).classList.add('hidden'); }
        else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro na rede.", "error"); }
    btn.innerText = "Enviar Código"; btn.disabled = false;
}

async function confirmarCadastro(e) {
    e.preventDefault();
    const payload = { email: document.getElementById('cadEmailAluno').value, codigo: document.getElementById('cadCodigo').value, nome: document.getElementById('cadNome').value, rm: document.getElementById('cadRM').value, senha: document.getElementById('cadSenha').value };
    try {
        const res = await fetch(`${API_URL}/api/auth/cadastrar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (data.success) {
            localStorage.setItem('aluno_token', data.token); localStorage.setItem('aluno_dados', JSON.stringify(data.aluno)); checarSessao();
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro.", "error"); }
}

async function confirmarRedefinicao(e) {
    e.preventDefault();
    const payload = { email: document.getElementById('recEmailAluno').value, codigo: document.getElementById('recCodigo').value, senha: document.getElementById('recSenha').value };
    try {
        const res = await fetch(`${API_URL}/api/auth/redefinir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (data.success) { mostrarToast("Senha alterada! Faça login.", "success"); alternarTelaAuth('login'); }
        else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro.", "error"); }
}

// --- FUNÇÕES GERAIS ---
function mostrarToast(mensagem, tipo = 'info') {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = `bg-card border border-color text-main px-4 py-3 rounded-xl flex items-center gap-3 toast-enter pointer-events-auto shadow-lg ${tipo==='success'?'text-emerald-400':tipo==='error'?'text-red-400':'text-blue-400'}`;
    t.innerHTML = `<p class="text-xs font-bold flex-grow">${mensagem}</p>`;
    c.appendChild(t); setTimeout(() => t.remove(), 4000);
}

function fecharZoomImagemDirect() {
    document.getElementById('modalZoomImagem').classList.remove('ativo'); document.body.style.overflow = '';
}
function fecharZoomImagem(e) { if (e.target.id === 'modalZoomImagem') fecharZoomImagemDirect(); }
function abrirZoomImagem(src) { document.getElementById('imgZoomConteudo').src = src; document.getElementById('modalZoomImagem').classList.add('ativo'); document.body.style.overflow = 'hidden'; }

function toggleConfigMenu() { document.getElementById('configMenu').classList.toggle('hidden'); }
function alternarModoEscuroClaro() { document.body.classList.toggle('light-theme'); document.body.classList.toggle('dark-theme'); }

function mudarAba(aba) {
    abaAtiva = aba;
    document.getElementById('catalogScreen').classList.toggle('hidden', aba !== 'catalogo');
    document.getElementById('muralScreen').classList.toggle('hidden', aba !== 'mural');
    document.getElementById('detailScreen').classList.add('hidden');
    document.getElementById('tabBtnCatalogo').className = aba === 'catalogo' ? "px-3 py-2 rounded-lg bg-header border border-red-500 text-xs font-bold text-main flex items-center gap-1.5" : "px-3 py-2 rounded-lg bg-card border border-color text-xs font-bold text-muted flex items-center gap-1.5";
    document.getElementById('tabBtnMural').className = aba === 'mural' ? "relative px-3 py-2 rounded-lg bg-header border border-amber-500 text-xs font-bold text-main flex items-center gap-1.5" : "relative px-3 py-2 rounded-lg bg-card border border-color text-xs font-bold text-muted hover:text-main transition flex items-center gap-1.5";
}

// --- MENU SUSPENSO DE CATEGORIAS ---
function toggleFiltroDropdown() {
    const menu = document.getElementById('dropdownFiltrosMenu');
    menu.classList.toggle('hidden');
}

window.addEventListener('click', (e) => {
    const dropdown = document.getElementById('dropdownFiltrosMenu');
    const btn = dropdown?.previousElementSibling;
    if (dropdown && !dropdown.contains(e.target) && !btn?.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});

function selecionarFiltroCategoria(catNome, catLabel) {
    categoriaAtual = catNome;
    document.getElementById('labelFiltroSelecionado').innerText = catLabel;
    document.getElementById('dropdownFiltrosMenu').classList.add('hidden');
    renderizarItens();
}

async function carregarCategoriasDinamicamente() {
    try {
        const res = await fetch(`${API_URL}/api/categorias`);
        if (res.ok) {
            const cats = await res.json();
            const containerOpcoes = document.getElementById('listaOpcoesFiltro');
            if(containerOpcoes) {
                containerOpcoes.innerHTML = '';
                cats.forEach(c => {
                    containerOpcoes.innerHTML += `<button onclick="selecionarFiltroCategoria('${c.nome}', '${c.nome}')" class="w-full text-left px-3 py-2.5 rounded-lg text-xs font-bold text-muted hover:text-main hover:bg-header transition">• ${c.nome}</button>`;
                });
            }
            const selectMural = document.getElementById('muralCategoria');
            if(selectMural) {
                selectMural.innerHTML = '';
                cats.forEach(c => { selectMural.innerHTML += `<option value="${c.nome}">${c.nome}</option>`; });
            }
        }
    } catch (e) {}
}

async function carregarItensDaAPI() {
    try {
        const response = await fetch(`${API_URL}/api/itens`);
        if (response.ok) { todosItens = await response.json(); renderizarItens(); }
    } catch(e){}
    setTimeout(() => document.getElementById('loadingOverlay').classList.add('hidden'), 500);
}

function normalizarStatus(status) { return (status || 'DISPONÍVEL').toUpperCase(); }

function renderizarItens() {
    const grid = document.getElementById('itemsGrid');
    grid.innerHTML = '';
    const filtrados = todosItens.filter(i => {
        const st = normalizarStatus(i.status);
        return (categoriaAtual === 'TODOS' || (i.categoria && i.categoria.toUpperCase() === categoriaAtual)) &&
               (statusAtual === 'TODOS' || st === statusAtual) &&
               (!termoBusca || (i.nome||'').toLowerCase().includes(termoBusca) || (i.txt_descricao||'').toLowerCase().includes(termoBusca));
    });
    filtrados.forEach(item => {
        const fotosArr = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
        const st = normalizarStatus(item.status);
        let badge = st === 'SOLICITADO' ? 'text-amber-400 border-amber-700/50 bg-amber-900/40' : (st === 'ENTREGUE' ? 'text-slate-400 border-slate-700 bg-slate-800' : 'text-emerald-400 border-emerald-700/50 bg-emerald-900/40');
        grid.innerHTML += `
            <div onclick='abrirDetalhes(${JSON.stringify(item).replace(/'/g, "&apos;")})' class="bg-card border border-color rounded-xl p-4 cursor-pointer shadow-sm hover:border-red-500/50 transition">
                ${fotosArr[0] ? `<img src="${fotosArr[0]}" class="w-full h-32 object-cover rounded-lg mb-3">` : `<div class="w-full h-32 bg-header border border-color rounded-lg mb-3 flex justify-center items-center text-muted"><i class="fas fa-box text-3xl"></i></div>`}
                <div class="flex justify-between items-center mb-1"><span class="text-[9px] font-bold px-2 py-0.5 rounded uppercase border">${item.categoria}</span><span class="text-[9px] font-bold px-2 py-0.5 rounded uppercase border ${badge}">${st}</span></div>
                <h4 class="font-bold text-sm text-main truncate mt-2">${item.nome || item.txt_descricao}</h4>
                <p class="text-[10px] text-muted mt-2"><i class="fas fa-map-marker-alt"></i> ${item.txt_local}</p>
            </div>
        `;
    });
}

function filtrarPorPalavraChave() { termoBusca = document.getElementById('searchInput').value.toLowerCase(); renderizarItens(); }
function limparBusca() { document.getElementById('searchInput').value = ''; termoBusca = ''; renderizarItens(); }
function filtrarStatus(st) { statusAtual = st; renderizarItens(); }

function abrirDetalhes(item) {
    itemSelecionado = item;
    document.getElementById('catalogScreen').classList.add('hidden');
    document.getElementById('detailScreen').classList.remove('hidden');
    document.getElementById('detailTitle').innerText = item.nome || item.txt_descricao;
    document.getElementById('detailDescription').innerText = item.txt_descricao;
    document.getElementById('detailLocal').innerText = item.txt_local;
    document.getElementById('detailDate').innerText = item.txt_data;
    
    const cont = document.getElementById('carouselContainer');
    cont.innerHTML = ''; fotosAtuais = item.fotos && item.fotos.length > 0 ? item.fotos : (item.foto ? [item.foto] : []);
    if(fotosAtuais.length > 0) {
        document.getElementById('detailPlaceholder').classList.add('hidden');
        fotosAtuais.forEach(f => cont.innerHTML += `<div class="w-full h-full flex-shrink-0 snap-center flex justify-center p-2"><img src="${f}" onclick="abrirZoomImagem('${f}')" class="max-h-full max-w-full object-contain rounded-lg"></div>`);
    } else document.getElementById('detailPlaceholder').classList.remove('hidden');
    
    const st = normalizarStatus(item.status);
    const b = document.getElementById('btnSolicitar');
    if (st !== 'DISPONÍVEL') { b.disabled = true; b.innerText = `STATUS: ${st}`; b.className = "w-full bg-gray-700 text-gray-400 font-bold py-3.5 rounded-xl text-sm"; }
    else { b.disabled = false; b.innerText = "ESTE É O MEU ITEM"; b.className = "w-full dynamic-btn font-bold py-3.5 rounded-xl text-sm"; }
}
function voltarParaCatalogo() { document.getElementById('detailScreen').classList.add('hidden'); if(abaAtiva === 'mural') document.getElementById('muralScreen').classList.remove('hidden'); else document.getElementById('catalogScreen').classList.remove('hidden'); }
function navegarFotos(dir) { const c = document.getElementById('carouselContainer'); if(fotosAtuais.length) { fotoIndiceAtual = (fotoIndiceAtual + dir + fotosAtuais.length) % fotosAtuais.length; c.scrollTo({ left: c.clientWidth * fotoIndiceAtual, behavior: 'smooth' }); } }

function abrirNovoModal() { if(itemSelecionado) document.getElementById('modalNovo').classList.remove('hidden'); }
async function enviarNovo() {
    const btn = document.getElementById('btnNovo'); btn.disabled = true; btn.innerText = "Processando...";
    try {
        const res = await fetch(`${API_URL}/api/solicitar`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('aluno_token')}` }, body: JSON.stringify({ id: itemSelecionado.id, nome: alunoSessao.nome, rm: alunoSessao.rm, email: alunoSessao.email }) });
        const data = await res.json();
        if(res.ok) { mostrarToast("Solicitação realizada! Vá até a secretaria.", "success"); document.getElementById('modalNovo').classList.add('hidden'); voltarParaCatalogo(); carregarItensDaAPI(); }
        else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro na solicitação", "error"); }
    btn.disabled = false; btn.innerText = "Sim, é meu!";
}

async function enviarAvisoMural(e) {
    e.preventDefault();
    const btn = document.getElementById('btnPublicarMural'); btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/mural`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('aluno_token')}` }, body: JSON.stringify({ nome: alunoSessao.nome, rm: alunoSessao.rm, email: alunoSessao.email, categoria: document.getElementById('muralCategoria').value, descricao: document.getElementById('muralDescricao').value }) });
        const data = await res.json();
        if (res.ok) { 
            document.getElementById('muralDescricao').value = ''; 
            if (data.matches_encontrados && data.matches_encontrados.length > 0) { 
                dispararNotificacaoNativa("Objeto Parecido Encontrado!", "O sistema achou algo parecido com o que você perdeu!");
                exibirMatchesImediatos(data.matches_encontrados); 
            } else {
                mostrarToast("Relato publicado! Avisaremos se acharmos.", "success"); 
            }
        }
    } catch { mostrarToast("Erro", "error"); }
    btn.disabled = false;
}
function exibirMatchesImediatos(itens) {
    const lst = document.getElementById('matchItensLista'); lst.innerHTML = '';
    itens.forEach(i => lst.innerHTML += `<div class="bg-header p-3 rounded-lg flex justify-between items-center gap-3"><div><p class="text-xs font-bold text-main">${i.nome || i.txt_descricao}</p></div><button onclick='abrirDetalhes(${JSON.stringify(i).replace(/'/g, "&apos;")}); document.getElementById("modalMatchImediato").classList.add("hidden");' class="dynamic-btn px-3 py-1 rounded text-[10px]">VER</button></div>`);
    document.getElementById('modalMatchImediato').classList.remove('hidden');
}

// --- CHAT MODERNO COM BOLHAS EM GRADIENTE VERMELHO ELEGANTE ---
function alternarJanelaChat() {
    chatAberto = !chatAberto;
    document.getElementById('janelaChat').classList.toggle('hidden', !chatAberto);
    document.getElementById('badgeChatWeb').classList.add('hidden');
    if (chatAberto) { atualizarMensagensChat(); chatTimerPolling = setInterval(atualizarMensagensChat, 3000); } else { clearInterval(chatTimerPolling); }
}
function abrirChatComItem() { if(!chatAberto) alternarJanelaChat(); if(itemSelecionado) document.getElementById('chatInputTexto').value = `Sobre o item #${itemSelecionado.id}: `; }

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
                if (ultimaMensagem.remetente !== 'ALUNO' && (document.hidden || !chatAberto)) {
                    dispararNotificacaoNativa("Secretaria ETEC respondeu", ultimaMensagem.mensagem);
                }
            }

            ultimaQtdMensagens = msgs.length; c.innerHTML = '';
            msgs.forEach(m => { 
                const eu = m.remetente === 'ALUNO'; 
                c.innerHTML += `
                    <div class="flex w-full ${eu ? 'justify-end' : 'justify-start'}">
                        <div class="flex items-end gap-2 max-w-[85%] ${eu ? 'flex-row-reverse' : 'flex-row'}">
                            ${!eu ? `<div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-red-600 to-rose-900 shadow-md"><i class="fas fa-shield-alt text-[10px] text-white"></i></div>` : ''}
                            <div class="rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-md ${eu ? 'rounded-tr-md bg-gradient-to-r from-red-600 to-rose-800 text-white shadow-[0_8px_24px_-4px_rgba(220,38,38,0.4)]' : 'rounded-tl-md border border-white/10 bg-zinc-800/90 text-zinc-100 backdrop-blur-sm'}">
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
        if((await fetch(`${API_URL}/api/chat/enviar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rm: alunoSessao.rm, nome: alunoSessao.nome, remetente: 'ALUNO', mensagem: txt }) })).ok) {
            document.getElementById('chatInputTexto').value = ''; atualizarMensagensChat();
        }
    } catch(e){}
}

// --- COLABORAÇÃO DO ALUNO (ACHEI ALGO) ---
function abrirModalCadastrarAluno() {
    const sel = document.getElementById('alunoItemCat');
    sel.innerHTML = document.getElementById('muralCategoria').innerHTML;
    document.getElementById('modalCadastrarAluno').classList.remove('hidden');
}

async function enviarCadastroAluno(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarAlunoItem');
    btn.innerText = "Enviando..."; btn.disabled = true;

    const fileInput = document.getElementById('alunoItemFoto');
    let fotoBase64 = "";

    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        reader.readAsDataURL(fileInput.files[0]);
        await new Promise(resolve => reader.onload = resolve);
        fotoBase64 = reader.result;
    }

    const payload = {
        nome: document.getElementById('alunoItemNome').value.trim(),
        descricao: document.getElementById('alunoItemDesc').value.trim(),
        categoria: document.getElementById('alunoItemCat').value,
        local: document.getElementById('alunoItemLocal').value.trim(),
        data: new Date().toLocaleDateString('pt-BR'),
        rm: alunoSessao.rm,
        fotos: fotoBase64 ? [fotoBase64] : []
    };

    try {
        const res = await fetch(`${API_URL}/api/itens/cadastrar-aluno`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            mostrarToast("Objeto enviado para moderação da secretaria!", "success");
            document.getElementById('modalCadastrarAluno').classList.add('hidden');
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro de rede.", "error"); }
    btn.innerText = "Enviar para a Secretaria"; btn.disabled = false;
}

// --- INICIALIZAÇÃO E GESTÃO DA SPLASH SCREEN (APENAS AO ENTRAR/RECARREGAR) ---
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
            }, 1000);
        };

        video.onended = encerrarSplash;
        
        setTimeout(() => {
            if (!splash.classList.contains('hidden')) {
                encerrarSplash();
            }
        }, 11000); 
    } else {
        checarSessao();
    }
};
