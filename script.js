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
let loteFotosAluno = 0;
let preparandoFotosAluno = false;
let envioCadastroAluno = false;

// ============================================================
// NOVO: COMPRESSOR INTELIGENTE DE FOTOS NO NAVEGADOR (HTML5 CANVAS)
// ============================================================
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
            ativarWebPush();
            mostrarToast("A permissão para notificações está ativa.", "success");
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") mostrarToast("Permissão para notificações concedida.", "success");
                if (permission === "granted") ativarWebPush();
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


const CORES_MATCH_ALUNO = ['preto', 'preta', 'azul', 'vermelho', 'vermelha', 'rosa', 'verde', 'amarelo', 'amarela', 'cinza', 'branco', 'branca', 'prata', 'dourado', 'marrom', 'roxo', 'roxa'];

function calcularSmartMatchAluno(relato, item) {
    let score = 0;
    let motivos = [];

    const catRelato = (relato.categoria || '').trim().toUpperCase();
    const catItem = (item.categoria || '').trim().toUpperCase();
    if (catRelato && catItem && catRelato === catItem) {
        score += 30;
        motivos.push(`Categoria ${catRelato}`);
    }

    const stopwords = new Set(['perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do', 'com', 'sem', 'favor', 'acho', 'que', 'objeto', 'achei']);
    function extrair(str) {
        return (str || '').toLowerCase().match(/[a-zA-Z0-9áéíóúãõâêîôûç]+/g) || [];
    }
    const termosRelato = extrair(relato.descricao).filter(p => p.length >= 3 && !stopwords.has(p));
    const termosItem = new Set(extrair(`${item.nome || ''} ${item.txt_descricao || ''}`).filter(p => p.length >= 3 && !stopwords.has(p)));
    
    const comuns = termosRelato.filter(t => termosItem.has(t));
    if (termosRelato.length > 0 && comuns.length > 0) {
        const pct = comuns.length / Math.max(1, termosRelato.length);
        score += Math.min(40, Math.round(pct * 40));
        motivos.push(`${comuns.slice(0, 2).join(', ')}`);
    }

    const coresRelato = extrair(relato.descricao).filter(p => CORES_MATCH_ALUNO.includes(p));
    const coresItem = new Set(extrair(`${item.nome || ''} ${item.txt_descricao || ''}`).filter(p => CORES_MATCH_ALUNO.includes(p)));
    const coresComuns = coresRelato.filter(c => coresItem.has(c));
    if (coresComuns.length > 0) {
        score += 15;
        motivos.push(`Cor ${coresComuns[0]}`);
    }

    return { score: Math.min(100, score), motivos };
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
    const token = SessaoPortal.token();
    const dados = SessaoPortal.dados();
    
    if (token && token.startsWith('token_prof_')) {
        fazerLogoff(false);
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
        return;
    }

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

        alunoSessao = dados;
        if (typeof CentralAvisos !== "undefined") CentralAvisos.carregar();
        ativarWebPush();
        document.getElementById('loginAlunoScreen').classList.add('hidden');
        document.getElementById('lblBemVindo').innerText = `Olá, ${alunoSessao.nome.split(' ')[0]}!`;
        
        document.getElementById('perfilNomeCompleto').innerText = alunoSessao.nome;
        document.getElementById('perfilEmailInstitucional').innerText = alunoSessao.email;
        document.getElementById('perfilRM').innerText = (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor') ? 'PROFESSOR (Apenas Cadastro)' : (alunoSessao.rm || 'N/A');

        // AJUSTES ESPECÍFICOS PARA PROFESSOR:
        const ehProf = /@(etec|cps)\.sp\.gov\.br$/i.test(alunoSessao.email || '') || alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor';
        const bPerdi = document.getElementById('btnPerdiBanner');
        if (bPerdi) bPerdi.classList.toggle('hidden', ehProf);
        const mMural = document.getElementById('menuBtnMural');
        if (mMural) mMural.classList.toggle('hidden', ehProf);
        if (ehProf) {
            document.getElementById('lblBemVindo').innerText = "Olá, Professor(a)!";
        }

        atualizarAcessoProfessor();
        carregarItensDaAPI();
        carregarCategoriasDinamicamente();
        
        if ("Notification" in window && Notification.permission === "default") {
            setTimeout(solicitarPermissaoNotificacao, 3000);
        }
    } else {
        if (token) SessaoPortal.limpar();
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
    }
}

function fazerLogoff(recarregar = true) {
    const limpezaPush = desativarWebPush(SessaoPortal.token());
    SessaoPortal.limpar();
    alunoSessao = null;
    if (recarregar) {
        return Promise.race([limpezaPush, new Promise(resolve => setTimeout(resolve, 1500))])
            .finally(() => window.location.reload());
    } else {
        document.getElementById('loginAlunoScreen').classList.remove('hidden');
    }
    return limpezaPush;
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
    if (authOcupada) return;
    document.getElementById('formLoginAluno').classList.add('hidden');
    document.getElementById('formCadastroAluno').classList.add('hidden');
    document.getElementById('formRecuperarAluno').classList.add('hidden');
    if (tela === 'login') document.getElementById('formLoginAluno').classList.remove('hidden');
    if (tela === 'cadastro') document.getElementById('formCadastroAluno').classList.remove('hidden');
    if (tela === 'recuperar') document.getElementById('formRecuperarAluno').classList.remove('hidden');
}

async function fazerLoginAluno(e) {
    e.preventDefault();
    if (!iniciarAnimacaoAuth('login')) return;
    const lembrar = document.getElementById('lembrarLogin').checked;
    let sucesso = false;
    try {
        const res = await fetch(API_URL + "/api/auth/login-aluno", {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email: document.getElementById('loginEmailAluno').value.trim(), 
                senha: document.getElementById('loginSenhaAluno').value.trim() 
            })
        });
        const data = await res.json();
        if (res.ok && data.success && data.token) {
            SessaoPortal.salvar(data.token, data.aluno, lembrar);
            document.getElementById('loginSenhaAluno').value = '';
            await confirmarAnimacaoAuth('login');
            await checarSessao();
            sucesso = true;
        } else {
            mostrarToast(data.message || "Erro no login.", "error");
        }
    } catch { 
        mostrarToast("Erro ao conectar com o servidor.", "error"); 
    } finally { encerrarAnimacaoAuth(sucesso); }
}

async function enviarCodigoAuth(idEmail, idBtn, idShow, idHide) {
    const email = document.getElementById(idEmail).value.trim();
    if (!/^[A-Z0-9._%+-]+@(aluno\.cps|cps|etec)\.sp\.gov\.br$/i.test(email)) return mostrarToast("Use seu e-mail institucional CPS ou ETEC.", "error");
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
    if (!iniciarAnimacaoAuth('cadastro')) return;
    const lembrar = document.getElementById('lembrarCadastro').checked;
    let sucesso = false;
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
        if (res.ok && data.success && data.token) {
            SessaoPortal.salvar(data.token, data.aluno, lembrar);
            document.getElementById('cadSenha').value = '';
            await confirmarAnimacaoAuth('cadastro');
            mostrarToast("Conta criada com sucesso!", "success");
            await checarSessao();
            sucesso = true;
        } else mostrarToast(data.message, "error");
    } catch { mostrarToast("Erro ao finalizar cadastro.", "error"); }
    finally { encerrarAnimacaoAuth(sucesso); }
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
        <i class="fas ${textoHTML(icone)} ${textoHTML(corIcone)} text-base shrink-0"></i>
        <p class="text-xs font-semibold flex-grow leading-snug">${textoHTML(mensagem)}</p>
        <button onclick="this.parentElement.remove()" class="text-slate-500 hover:text-white text-xs"><i class="fas fa-times"></i></button>
    `;
    t.setAttribute('role', tipo === 'error' ? 'alert' : 'status');
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
    const url = urlImagemSegura(src);
    if (!url) return;
    document.getElementById('imgZoomConteudo').src = url;
    document.getElementById('modalZoomImagem').classList.add('ativo'); 
    document.body.style.overflow = 'hidden'; 
}

function mudarAba(aba) {
    abaAtiva = aba;
    document.getElementById('catalogScreen').classList.toggle('hidden', aba !== 'catalogo');
    document.getElementById('muralScreen').classList.toggle('hidden', aba !== 'mural');
    document.getElementById('meusItensScreen').classList.toggle('hidden', aba !== 'meusItens');
    document.getElementById('detailScreen').classList.add('hidden');
    if (aba === 'mural') { carregarMuralPublico(); if (typeof Rascunhos !== 'undefined') Rascunhos.restaurar('mural'); }
}

async function abrirPainelMeusItens() {
    mudarAba('meusItens');
    if (typeof MeusCadastros !== 'undefined') MeusCadastros.carregar();
    if (!alunoSessao) return;
    const headers = { 'Authorization': `Bearer ${SessaoPortal.token() || ''}` };

    const listaSol = document.getElementById('listaMinhasSolicitacoes');
    const listaRel = document.getElementById('listaMeusRelatosMural');
    
    listaSol.innerHTML = `<p class="text-xs text-slate-500 italic">Buscando solicitações...</p>`;
    listaRel.innerHTML = `<p class="text-xs text-slate-500 italic">Buscando relatos...</p>`;

    try {
        const resItens = await fetch(`${API_URL}/api/itens/meus`, { headers });
        if (resItens.ok) {
            const itens = await resItens.json();
            const meus = itens;
            
            if (meus.length > 0) {
                listaSol.innerHTML = '';
                meus.forEach(i => {
                    const st = normalizarStatus(i);
                    listaSol.innerHTML += `
                        <div class="glass-panel rounded-2xl p-4 flex justify-between items-center gap-3 border border-white/5">
                            <div>
                                <p class="text-xs font-bold text-white">${textoHTML(i.nome || i.txt_descricao)}</p>
                                <p class="text-[10px] text-slate-400 mt-0.5">Status: <span class="font-bold text-amber-400 uppercase">${textoHTML(st)}</span></p>
                            </div>
                            <button onclick="abrirDetalhes(${argumentoHTML(i)})" class="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-white transition">VER</button>
                        </div>`;
                });
            } else listaSol.innerHTML = `<p class="text-xs text-slate-500 italic">Você ainda não solicitou nenhum item.</p>`;
        }

        const resMural = await fetch(`${API_URL}/api/mural/aluno/${encodeURIComponent(alunoSessao.rm)}`, { headers });
        if (resMural.ok) {
            const relatos = await resMural.json();
            if (relatos.length > 0) {
                listaRel.innerHTML = '';
                relatos.forEach(r => {
                    const matches = [];
                    (todosItens || []).forEach(it => {
                        const st = normalizarStatus(it);
                        if (st === 'DISPONÍVEL') {
                            const res = calcularSmartMatchAluno(r, it);
                            if (res.score >= 50) matches.push({ item: it, score: res.score });
                        }
                    });
                    matches.sort((a, b) => b.score - a.score);

                    let htmlMatchBadge = '';
                    if (matches.length > 0) {
                        const top = matches[0];
                        htmlMatchBadge = `
                            <div class="mt-2.5 pt-2.5 border-t border-white/5 flex items-center justify-between">
                                <span class="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5">
                                    <i class="fas fa-magic"></i> Encontramos item compatível (${textoHTML(top.score)}%)
                                </span>
                                <button onclick="abrirDetalhes(${argumentoHTML(top.item)})" class="px-3 py-1 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-[11px] font-bold text-emerald-300 transition">
                                    Ver Objeto
                                </button>
                            </div>
                        `;
                    }

                    listaRel.innerHTML += `
                        <div class="glass-panel rounded-2xl p-4 border border-white/5">
                            <div class="flex justify-between items-center gap-3">
                                <div>
                                    <p class="text-xs font-bold text-white"><span class="text-amber-400">[${textoHTML(r.categoria)}]</span> ${textoHTML(r.descricao)}</p>
                                    <p class="text-[10px] text-slate-400 mt-0.5">Data do registro: ${textoHTML(r.data || 'Recente')}</p>
                                </div>
                                <span class="text-[10px] font-black px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wider shrink-0">ATIVO</span>
                            </div>
                            ${htmlMatchBadge}
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
                        <button id="chipCat_${textoHTML(c.nome)}" onclick="selecionarFiltroCategoria(${argumentoHTML(c.nome)}, ${argumentoHTML(c.nome)})" class="category-chip px-3.5 py-1.5 rounded-xl text-xs font-bold border transition shrink-0 bg-white/5 text-slate-300 border-white/10 hover:bg-white/10">
                            ${textoHTML(c.nome)}
                        </button>`;
                });
            }
            if (selectMural) {
                selectMural.innerHTML = '';
                cats.forEach(c => { selectMural.innerHTML += `<option value="${textoHTML(c.nome)}">${textoHTML(c.nome)}</option>`; });
            }
            if (selectAlunoCad) {
                selectAlunoCad.innerHTML = '';
                cats.forEach(c => { selectAlunoCad.innerHTML += `<option value="${textoHTML(c.nome)}">${textoHTML(c.nome)}</option>`; });
            }
            if (typeof Rascunhos !== 'undefined') { Rascunhos.restaurar('mural'); Rascunhos.restaurar('encontrado'); }
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
            <div onclick="abrirDetalhes(${argumentoHTML(item)})" class="interactive-card glass-panel rounded-3xl p-4 cursor-pointer flex flex-col justify-between group border border-white/10">
                <div>
                    <div class="relative w-full h-44 rounded-2xl overflow-hidden mb-3.5 bg-black/40 border border-white/5">
                        ${imagemSrc ? `<img src="${imagemHTML(imagemSrc)}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">` : `<div class="w-full h-full flex flex-col justify-center items-center text-slate-600"><i class="fas fa-box text-3xl mb-1"></i><span class="text-[10px] font-bold">Sem imagem</span></div>`}
                        <div class="absolute top-2.5 left-2.5">
                            <span class="text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider bg-black/70 backdrop-blur-md text-white border border-white/10 shadow-sm">${textoHTML(item.categoria)}</span>
                        </div>
                        <div class="absolute top-2.5 right-2.5">
                            <span class="text-[10px] font-black px-2.5 py-1 rounded-lg uppercase tracking-wider border shadow-sm ${textoHTML(badgeCor)}">
                                ${textoHTML(st)}
                            </span>
                        </div>
                        ${fotosArray.length > 1 ? `<div class="absolute bottom-2.5 right-2.5 bg-black/70 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded-md border border-white/10"><i class="fas fa-images mr-1"></i>${textoHTML(fotosArray.length)}</div>` : ''}
                    </div>

                    <h4 class="font-extrabold text-sm text-white truncate tracking-tight">${textoHTML(item.nome || item.txt_descricao)}</h4>
                    <p class="text-xs text-slate-400 line-clamp-2 mt-1 leading-snug">${textoHTML(item.txt_descricao)}</p>
                </div>

                <div class="pt-3 mt-3 border-t border-white/5 flex justify-between items-center text-[11px] text-slate-400">
                    <span class="truncate max-w-[150px]"><i class="fas fa-map-marker-alt text-red-500 mr-1"></i>${textoHTML(item.txt_local)}</span>
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
            cont.innerHTML += `<div class="w-full h-full flex-shrink-0 snap-center flex justify-center items-center p-2"><img src="${imagemHTML(f)}" onclick="abrirZoomImagem(${argumentoHTML(urlImagemSegura(f))})" class="max-h-full max-w-full object-contain rounded-xl cursor-zoom-in"></div>`;
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
    const ehProf = alunoSessao && (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor');
    if (ehProf) {
        b.disabled = true;
        b.innerText = "PROFESSORES NÃO PODEM SOLICITAR ITENS";
        b.className = "w-full bg-slate-800 text-slate-400 font-bold py-3.5 rounded-xl text-xs uppercase cursor-not-allowed border border-white/5 opacity-80";
    } else if (st !== 'DISPONÍVEL') { 
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
        c.scrollTo({ left: c.clientWidth * fotoIndiceAtual, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
        document.getElementById('photoCurrentIdx').innerText = fotoIndiceAtual + 1;
    } 
}

function abrirNovoModal() { 
    if (alunoSessao && (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor')) {
        return mostrarToast("Conta de professor autorizada apenas para cadastrar itens, não para solicitar.", "error");
    }
    if(itemSelecionado) document.getElementById('modalNovo').classList.remove('hidden'); 
}

async function enviarNovo() {
    if (alunoSessao && (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor')) {
        return mostrarToast("Conta de professor autorizada apenas para cadastrar itens, não para solicitar.", "error");
    }
    const btn = document.getElementById('btnNovo'); 
    btn.disabled = true; btn.innerText = "Processando...";
    try {
        const token = SessaoPortal.token();
        const res = await fetch(`${API_URL}/api/solicitar`, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            }, 
            body: JSON.stringify({ id: itemSelecionado.id })
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
    if (alunoSessao && (alunoSessao.rm === 'PROFESSOR' || alunoSessao.role === 'professor')) {
        return mostrarToast("Conta de professor autorizada apenas para cadastrar itens encontrados.", "error");
    }
    const btn = document.getElementById('btnPublicarMural'); 
    btn.disabled = true;
    try {
        const token = SessaoPortal.token();
        const res = await fetch(`${API_URL}/api/mural`, { 
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json', 
                'Authorization': `Bearer ${token}` 
            }, 
            body: JSON.stringify({ 
                categoria: document.getElementById('muralCategoria').value, 
                descricao: document.getElementById('muralDescricao').value.trim() 
            }) 
        });
        const data = await res.json();
        if (res.ok && data.success) { 
            if (typeof Rascunhos !== 'undefined') Rascunhos.limpar('mural');
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
                        <span class="text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20">${textoHTML(m.categoria)}</span>
                        <span class="text-[10px] text-slate-500">${textoHTML(m.data_registro || '')}</span>
                    </div>
                    <p class="text-xs text-slate-200 font-medium">"${textoHTML(m.descricao)}"</p>
                    <p class="text-[10px] text-slate-400 font-bold"><i class="fas fa-user text-slate-500 mr-1"></i>${textoHTML(m.nome_aluno)}</p>
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
                    <p class="text-xs font-bold text-white">${textoHTML(i.nome || i.txt_descricao)}</p>
                    <span class="text-[9px] uppercase font-bold text-emerald-400">${textoHTML(i.categoria)}</span>
                </div>
                <button onclick="abrirDetalhes(${argumentoHTML(i)}); document.getElementById('modalMatchImediato').classList.add('hidden');" class="px-3 py-1.5 rounded-xl bg-red-600 text-white font-bold text-xs">VER</button>
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
        const res = await fetch(`${API_URL}/api/chat/mensagens/${encodeURIComponent(alunoSessao.rm)}?marcar_lida=true`, {
            headers: { 'Authorization': `Bearer ${SessaoPortal.token() || ''}` }
        });
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
                    <div class="flex w-full ${textoHTML(eu ? 'justify-end' : 'justify-start')}">
                        <div class="flex items-end gap-2 max-w-[85%] ${textoHTML(eu ? 'flex-row-reverse' : 'flex-row')}">
                            ${!eu ? `<div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-red-600 to-rose-600 shadow-md text-white"><i class="fas fa-shield-alt text-[10px]"></i></div>` : ''}
                            <div class="rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-sm ${textoHTML(eu ? 'rounded-tr-sm bg-gradient-to-r from-red-600 to-rose-600 text-white' : 'rounded-tl-sm border border-white/10 bg-[#161c28] text-slate-200')}">
                                ${textoHTML(m.mensagem)}
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
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${SessaoPortal.token() || ''}` },
            body: JSON.stringify({ rm: alunoSessao.rm, nome: alunoSessao.nome, remetente: 'ALUNO', mensagem: txt }) 
        });
        if(res.ok) {
            document.getElementById('chatInputTexto').value = ''; 
            atualizarMensagensChat();
        }
    } catch(e){}
}

function abrirModalCadastrarAluno() {
    if (envioCadastroAluno) return;
    loteFotosAluno++; preparandoFotosAluno = false;
    document.getElementById('alunoItemFoto').disabled = false;
    document.getElementById('alunoItemFoto').value = '';
    document.getElementById('btnSalvarAlunoItem').disabled = false;
    document.getElementById('gridPreviewAluno').inert = false;
    ocultarEstadoFotos('statusCompressaoFotos');
    document.getElementById('btnAutoPreencherIAAluno').disabled = false;
    renderizarGridPreviewAluno();
        const btnIAAluno = document.getElementById('btnAutoPreencherIAAluno');
        if (btnIAAluno) {
            if (fotosAlunoSelecionadas && fotosAlunoSelecionadas.length > 0) btnIAAluno.classList.remove('hidden');
            else btnIAAluno.classList.add('hidden');
        }
    const badge = document.getElementById('statusCompressaoFotos');
    if (badge) badge.classList.add('hidden');
    document.getElementById('modalCadastrarAluno').classList.remove('hidden');
    if (typeof Rascunhos !== 'undefined') Rascunhos.restaurar('encontrado');
}

// ATUALIZADO: COMPRESSÃO AUTOMÁTICA DE IMAGENS DO CELULAR
async function prepararFotosAluno(input) {
    if (envioCadastroAluno || !input.files?.length) return;
    const lote = ++loteFotosAluno;
    const arquivos = Array.from(input.files).slice(0, 4 - fotosAlunoSelecionadas.length);
    if (!arquivos.length) {
        mostrarEstadoFotos('statusCompressaoFotos', 'erro', 'Limite de 4 fotos. Remova uma antes de adicionar outra.');
        input.value = ''; return;
    }
    preparandoFotosAluno = true; input.disabled = true;
    document.getElementById('btnSalvarAlunoItem').disabled = true;
    document.getElementById('btnAutoPreencherIAAluno').disabled = true;
    document.getElementById('gridPreviewAluno').inert = true;
    let falhas = 0;
    try {
        for (let i = 0; i < arquivos.length; i++) {
            mostrarEstadoFotos('statusCompressaoFotos', 'preparando', `Preparando foto ${i + 1} de ${arquivos.length}…`);
            try {
                const foto = await comprimirImagem(arquivos[i]);
                if (lote !== loteFotosAluno) return;
                fotosAlunoSelecionadas.push(foto);
            } catch (error) { falhas++; }
            if (lote !== loteFotosAluno) return;
        }
        renderizarGridPreviewAluno();
        document.getElementById('btnAutoPreencherIAAluno').classList.toggle('hidden', !fotosAlunoSelecionadas.length);
        mostrarEstadoFotos('statusCompressaoFotos', falhas ? 'erro' : 'prontas', falhas
            ? `${falhas} foto(s) não puderam ser abertas. As demais foram preservadas; tente selecionar novamente.`
            : `${fotosAlunoSelecionadas.length} foto(s) prontas. O envio acontece ao salvar o item.`);
    } finally {
        if (lote === loteFotosAluno) {
            preparandoFotosAluno = false; input.disabled = false; input.value = '';
            document.getElementById('btnSalvarAlunoItem').disabled = false;
            document.getElementById('btnAutoPreencherIAAluno').disabled = false;
            document.getElementById('gridPreviewAluno').inert = false;
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
                    <img src="${imagemHTML(f)}" class="w-full h-full object-cover rounded-xl border border-white/10">
                    <button type="button" onclick="fotosAlunoSelecionadas.splice(${textoHTML(i)}, 1); renderizarGridPreviewAluno();
        const btnIAAluno = document.getElementById('btnAutoPreencherIAAluno');
        if (btnIAAluno) {
            if (fotosAlunoSelecionadas && fotosAlunoSelecionadas.length > 0) btnIAAluno.classList.remove('hidden');
            else btnIAAluno.classList.add('hidden');
        }" class="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-[10px]"><i class="fas fa-times"></i></button>
                </div>`;
        });
    } else container.classList.add('hidden');
}

async function enviarCadastroAluno(e) {
    e.preventDefault();
    if (envioCadastroAluno) return;
    if (preparandoFotosAluno) return mostrarToast('Aguarde a preparação das fotos.', 'info');
    envioCadastroAluno = true;
    document.getElementById('alunoItemFoto').disabled = true;
    document.getElementById('gridPreviewAluno').inert = true;
    document.getElementById('btnAutoPreencherIAAluno').disabled = true;
    mostrarEstadoFotos('statusCompressaoFotos', 'enviando', fotosAlunoSelecionadas.length ? 'Enviando fotos e salvando o item…' : 'Salvando o item…');
    const btn = document.getElementById('btnSalvarAlunoItem');
    btn.innerText = "Enviando..."; btn.disabled = true;

    const payload = {
        nome: document.getElementById('alunoItemNome').value.trim(),
        descricao: document.getElementById('alunoItemDesc').value.trim(),
        categoria: document.getElementById('alunoItemCat').value,
        local: document.getElementById('alunoItemLocal').value.trim(),
        data: new Date().toLocaleDateString('pt-BR'),
        fotos: fotosAlunoSelecionadas,
        foto: fotosAlunoSelecionadas[0] || ""
    };

    try {
        const token = SessaoPortal.token();
        const res = await fetch(`${API_URL}/api/itens/cadastrar-aluno`, {
            method: 'POST', 
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            mostrarEstadoFotos('statusCompressaoFotos', 'sucesso', 'Envio concluído!');
            mostrarToast(fotosAlunoSelecionadas.length ? "Fotos enviadas! Item aguardando moderação." : "Objeto enviado para moderação da secretaria!", "success");
            document.getElementById('modalCadastrarAluno').classList.add('hidden');
            if (typeof Rascunhos !== 'undefined') Rascunhos.limpar('encontrado');
            fotosAlunoSelecionadas = [];
            renderizarGridPreviewAluno();
            e.target.reset();
        } else {
            mostrarEstadoFotos('statusCompressaoFotos', 'erro', 'O envio não foi concluído. Suas fotos foram mantidas para tentar novamente.');
            mostrarToast(data.message || 'Não foi possível salvar.', 'error');
        }
    } catch {
        mostrarEstadoFotos('statusCompressaoFotos', 'erro', 'Falha de conexão. Suas fotos foram mantidas para tentar novamente.');
        mostrarToast('Erro ao conectar.', 'error');
    } finally {
        envioCadastroAluno = false;
        document.getElementById('alunoItemFoto').disabled = false;
        document.getElementById('gridPreviewAluno').inert = false;
        document.getElementById('btnAutoPreencherIAAluno').disabled = false;
        btn.innerText = 'Enviar para Moderação da Secretaria'; btn.disabled = false;
    }
}

window.onload = () => { 
    document.body.classList.add('dark-theme'); 
    const splash = document.getElementById('splashScreenAnimacao');
    const video = document.getElementById('videoSplash');

    const splashJaExibido = sessionStorage.getItem('splash_ja_exibido') === 'true';
    if (splashJaExibido && splash) {
        splash.classList.add('hidden');
        splash.style.display = 'none';
        checarSessao();
        return;
    }

    if (splash && video) {
        sessionStorage.setItem('splash_ja_exibido', 'true');
        
        const encerrarSplash = () => {
            splash.classList.add('opacity-0');
            setTimeout(() => { 
                splash.classList.add('hidden'); 
                splash.style.display = 'none'; 
                checarSessao(); 
            }, 700);
        };

        video.muted = true;
        video.defaultMuted = true;
        video.play().catch(() => {});
        video.onended = encerrarSplash;

        // Tempo limite de segurança de 4 segundos para o vídeo
        setTimeout(() => { 
            if (!splash.classList.contains('hidden')) encerrarSplash(); 
        }, 4500); 
    } else {
        checarSessao();
    }
};


// ==============================================================================
// REFRESH INTELIGENTE DO PORTAL DO ALUNO (SEM RECARREGAR PÁGINA E SEM SPLASH)
// ==============================================================================
async function atualizarPortalAluno() {
    const icone = document.getElementById('iconeRefreshPortal');
    const btn = document.getElementById('btnRefreshPortal');
    if (icone) icone.classList.add('fa-spin');
    if (btn) btn.disabled = true;

    try {
        await Promise.all([
            typeof carregarItensDaAPI === 'function' ? carregarItensDaAPI() : Promise.resolve(),
            typeof carregarCategoriasDinamicamente === 'function' ? carregarCategoriasDinamicamente() : Promise.resolve(),
            typeof carregarMuralPublico === 'function' ? carregarMuralPublico() : Promise.resolve(),
            typeof atualizarMensagensChat === 'function' && chatAberto ? atualizarMensagensChat() : Promise.resolve()
        ]);
        mostrarToast("Catálogo e pertences atualizados!", "success");
    } catch (err) {
        mostrarToast("Erro ao sincronizar dados com o servidor.", "error");
    } finally {
        setTimeout(() => {
            if (icone) icone.classList.remove('fa-spin');
            if (btn) btn.disabled = false;
        }, 500);
    }
}


// ==============================================================================
// FASE 3: AUTO-PREENCHIMENTO COM IA (VISÃO COMPUTACIONAL MULTIMODAL)
// ==============================================================================
async function analisarFotoAlunoComIA() {
    if (!fotosAlunoSelecionadas || fotosAlunoSelecionadas.length === 0) {
        return mostrarToast("Selecione uma foto primeiro.", "info");
    }
    const fotoAnalisada = fotosAlunoSelecionadas[0];
    const btn = document.getElementById('btnAutoPreencherIAAluno');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Analisando com IA...';
        btn.disabled = true;
    }

    try {
        const res = await fetch(API_URL + "/api/ia/analisar-imagem", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ foto: fotoAnalisada })
        });
        const data = await res.json();
        if (envioCadastroAluno || fotosAlunoSelecionadas[0] !== fotoAnalisada) return;
        if (res.ok && data.success && data.resultado) {
            const r = data.resultado;
            const aplicado = aplicarSugestaoVisual(r, {
                nome: document.getElementById('alunoItemNome'),
                descricao: document.getElementById('alunoItemDesc'),
                categoria: document.getElementById('alunoItemCat')
            });
            if (aplicado && typeof Rascunhos !== 'undefined') Rascunhos.salvar('encontrado');
            mostrarToast(aplicado ? 'Sugestões preenchidas. Confira a foto antes de salvar.' :
                (r.aviso || 'Não foi possível identificar o objeto. Preencha os campos manualmente.'), aplicado ? 'success' : 'info');
        } else {
            mostrarToast(data.message || "Não foi possível analisar os detalhes.", "error");
        }
    } catch (err) {
        mostrarToast("Erro ao conectar ao serviço de inteligência artificial.", "error");
    } finally {
        if (btn) {
            btn.innerHTML = '<i class="fas fa-wand-magic-sparkles mr-1"></i> ✨ Preencher com Inteligência Artificial';
            btn.disabled = false;
        }
    }
}

