/* Navegação por teclado compartilhada entre portal e secretaria. */
const Acessibilidade = {
    ativo: null, retorno: new WeakMap(), inertes: new Map(), agendado: false,
    seletor: '.modal-overlay, #modalErroDetalhado, #centralAvisos, #modalNovo, #modalCadastrarAluno, #modalMatchImediato, #modalZoomImagem, #loginAlunoScreen, #loginScreen, #menuLateral.aberto',
    visivel(el) { return !!el && !el.hidden && !el.classList.contains('hidden') && getComputedStyle(el).visibility !== 'hidden' && el.getClientRects().length > 0; },
    focaveis(el) { return Array.from(el.querySelectorAll('button,a[href],input,select,textarea,[tabindex="0"]')).filter(x => !x.disabled && !x.closest('[inert]') && this.visivel(x)); },
    preparar() {
        for(const icon of document.querySelectorAll('i.fas,i.far,i.fab,i.fa-solid,i.fa-regular'))icon.setAttribute('aria-hidden','true');
        for (const el of document.querySelectorAll(this.seletor)) {
            el.setAttribute('role','dialog'); el.setAttribute('aria-modal','true'); el.tabIndex = -1;
            const titulo = el.querySelector('h2,h3');
            if (titulo) { if (!titulo.id) titulo.id = 'titulo-' + el.id; el.setAttribute('aria-labelledby',titulo.id); }
            else el.setAttribute('aria-label',el.id === 'modalZoomImagem' ? 'Foto ampliada do objeto' : 'Entrar na conta');
        }
        const nomes = {cadNome:'Nome completo',cadRM:'Registro de matrícula (RM)',cadSenha:'Senha da nova conta',cadEmailAluno:'E-mail institucional',cadCodigo:'Código de confirmação do e-mail',recCodigo:'Código de recuperação',recSenha:'Nova senha',chatInputTexto:'Mensagem para a secretaria',inputChatMsg:'Resposta ao aluno',searchInput:'Buscar objetos',inputBusca:'Buscar itens cadastrados'};
        for (const el of document.querySelectorAll('input:not([type="hidden"]),textarea,select')) {
            if (!el.id) continue;
            const label = Array.from(document.querySelectorAll('label')).find(x => x.htmlFor === el.id || x.contains(el));
            if (label || el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby')) continue;
            const anterior = el.previousElementSibling;
            const perto = anterior?.tagName === 'LABEL' ? anterior : el.parentElement.querySelector('label');
            if (perto && !perto.htmlFor) perto.htmlFor = el.id;
            else {
                const novo = document.createElement('label'); novo.className = 'sr-only-acessivel'; novo.htmlFor = el.id;
                novo.textContent = nomes[el.id] || el.placeholder || 'Escolha uma opção'; el.before(novo);
            }
        }
        for (const el of document.querySelectorAll('button')) {
            if (el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby') || el.innerText.trim().replace(/[✕×]/g,'').trim()) continue;
            const fn = el.getAttribute('onclick') || '';
            let nome = el.title;
            if (!nome) {
                if (/Perfil/.test(fn)) nome = 'Abrir perfil';
                else if (/MenuNavegacao/.test(fn)) nome = 'Abrir navegação';
                else if (/navegarFotos\(-1/.test(fn)) nome = 'Foto anterior';
                else if (/navegarFotos/.test(fn)) nome = 'Próxima foto';
                else if (/splice/.test(fn)) nome = 'Remover foto selecionada';
                else if (/alternarJanelaChat/.test(fn)) nome = 'Abrir ou fechar conversa com a secretaria';
                else if (el.querySelector('.fa-paper-plane')) nome = 'Enviar mensagem';
                else if (el.querySelector('.fa-eye')) nome = 'Mostrar ou ocultar senha';
                else nome = 'Fechar janela';
            }
            el.setAttribute('aria-label',nome);
        }
        for (const el of document.querySelectorAll('.interactive-card[onclick],img[onclick]:not(#imgZoomConteudo)')) {
            if (el.dataset.teclado) continue;
            el.dataset.teclado = 'true'; el.tabIndex = 0; el.setAttribute('role','button');
            el.setAttribute('aria-label',el.querySelector('h4')?.textContent || 'Ampliar foto do objeto');
            el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); } });
        }
        for (const img of document.querySelectorAll('img:not([alt])')) img.alt = img.closest('.interactive-card')?.querySelector('h4')?.textContent || 'Foto do objeto';
        for (const [id, nome] of [['menuNavegacaoDropdown','Navegação do portal'],['perfilMenu','Sua conta'],['dropdownStatusMenu','Filtro por situação'],['menuLateral','Navegação da secretaria']]) {
            const menu = document.getElementById(id); if (!menu) continue;
            if (id === 'menuLateral') { const aberto = menu.classList.contains('aberto'); menu.inert = !aberto; menu.setAttribute('aria-hidden',String(!aberto)); }
            const btn = id === 'menuLateral' ? document.getElementById('btnHamburger') : id === 'dropdownStatusMenu' ? document.getElementById('btnDropdownStatus') : menu.previousElementSibling;
            if (!btn || btn.tagName !== 'BUTTON') continue;
            btn.setAttribute('aria-controls', id); btn.setAttribute('aria-expanded', String(id === 'menuLateral' ? menu.classList.contains('aberto') : this.visivel(menu)));
            menu.setAttribute('aria-label',nome);
        }
    },
    sincronizar() {
        this.preparar();
        const lista = Array.from(document.querySelectorAll(this.seletor)).filter(el => this.visivel(el));
        lista.sort((a,b) => (parseInt(getComputedStyle(a).zIndex)||0) - (parseInt(getComputedStyle(b).zIndex)||0));
        const topo = lista.at(-1) || null;
        if (topo === this.ativo) return;
        const anterior = this.ativo;
        for (const [el, estado] of this.inertes) el.inert = estado;
        this.inertes.clear(); this.ativo = topo;
        if (topo) {
            if (!this.retorno.has(topo) || !lista.includes(anterior)) this.retorno.set(topo,document.activeElement);
            for (const el of document.body.children) {
                if (!el.contains(topo) && !['SCRIPT','STYLE','LINK'].includes(el.tagName)) { this.inertes.set(el,el.inert); el.inert = true; }
            }
            if (!topo.contains(document.activeElement)) (this.focaveis(topo)[0] || topo).focus({preventScroll:true});
        } else if (anterior) {
            const alvo = this.retorno.get(anterior); this.retorno.delete(anterior);
            if (alvo?.isConnected && this.visivel(alvo)) alvo.focus({preventScroll:true});
        }
    },
    fechar() {
        const el = this.ativo;
        if (!el || ['loginAlunoScreen','loginScreen'].includes(el.id)) return;
        if (el.id === 'modalCadastrarAluno' && typeof envioCadastroAluno !== 'undefined' && envioCadastroAluno) return;
        if (el.id === 'modalFormItem' && typeof envioItemSecretaria !== 'undefined' && envioItemSecretaria) return;
        if (el.id === 'menuLateral') { toggleMenuHamburger(); return; }
        if (el.id === 'modalConfirmacao') { document.getElementById('btnConfirmModalCancelar').click(); return; }
        if (el.id === 'modalAlertaBonito') { document.getElementById('btnAlertaOk').click(); return; }
        if (el.id === 'modalZoomImagem') { fecharZoomImagemDirect(); return; }
        el.classList.add('hidden');
    },
    iniciar() {
        this.sincronizar();
        const main = document.querySelector('main');
        if (main) {
            main.id = 'conteudoPrincipal'; main.tabIndex = -1;
            const pular = document.createElement('a'); pular.href = '#conteudoPrincipal'; pular.className = 'pular-conteudo'; pular.textContent = 'Pular para o conteúdo';
            document.body.prepend(pular);
        }
        document.getElementById('toastContainer')?.setAttribute('aria-live','polite');
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                if (this.ativo) this.fechar();
                else {
                    for (const id of ['menuNavegacaoDropdown','perfilMenu','dropdownStatusMenu']) document.getElementById(id)?.classList.add('hidden');
                    if (document.getElementById('menuLateral')?.classList.contains('aberto')) toggleMenuHamburger();
                }
            }
            if (e.key !== 'Tab' || !this.ativo) return;
            const itens = this.focaveis(this.ativo); const primeiro = itens[0]; const ultimo = itens.at(-1);
            if (!primeiro) { e.preventDefault(); this.ativo.focus(); return; }
            if (e.shiftKey && (document.activeElement === primeiro || !this.ativo.contains(document.activeElement))) { e.preventDefault(); ultimo.focus(); }
            else if (!e.shiftKey && (document.activeElement === ultimo || !this.ativo.contains(document.activeElement))) { e.preventDefault(); primeiro.focus(); }
        });
        new MutationObserver(() => this.sincronizar()).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden']});
    }
};
document.addEventListener('DOMContentLoaded', () => Acessibilidade.iniciar());
