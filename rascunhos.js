/* Somente texto; nunca guarda senha, token ou imagem no rascunho. */
const Rascunhos = {
    prefixo: 'etec-rascunho-v1:', ttl: 24 * 60 * 60 * 1000,
    formularios: {
        encontrado: ['alunoItemNome', 'alunoItemDesc', 'alunoItemCat', 'alunoItemLocal', 'alunoItemData'],
        mural: ['muralCategoria', 'muralDescricao'],
        secretaria: ['formItemNome', 'formItemDescricao', 'formItemCategoria', 'formItemLocal', 'formItemData', 'formItemStatus']
    },
    conta() {
        try {
            if (typeof SessaoPortal !== 'undefined' && SessaoPortal.dados()) return SessaoPortal.dados().email;
            const token = sessionStorage.getItem('secretaria_token') || localStorage.getItem('secretaria_token');
            const valor = token?.split('.')[1];
            const payload = JSON.parse(atob(valor.replace(/-/g, '+').replace(/_/g, '/')));
            return typeof payload.email === 'string' ? payload.email : null;
        } catch (_) { return null; }
    },
    chave(tipo) { const email = this.conta(); return email ? `${this.prefixo}${encodeURIComponent(email)}:${tipo}` : null; },
    editando(tipo) { return (tipo === 'secretaria' && !!document.getElementById('formItemId')?.value) || (tipo==='encontrado' && typeof CorrecaoCadastro!=='undefined' && !!CorrecaoCadastro.atual); },
    avisar(tipo, texto) { const el = document.getElementById('rascunho-' + tipo); if (el) el.textContent = texto; },
    salvar(tipo) {
        if (this.editando(tipo)) return;
        const chave = this.chave(tipo); if (!chave) return;
        try {
            const campos = {};
            for (const id of this.formularios[tipo]) campos[id] = (document.getElementById(id)?.value || '').slice(0, 4000);
            const preenchido = Object.entries(campos).some(([id, value]) => value.trim() && !['alunoItemCat','muralCategoria','formItemCategoria','formItemData','formItemStatus','alunoItemData'].includes(id));
            if (!preenchido) { sessionStorage.removeItem(chave); this.avisar(tipo,'Rascunho vazio.'); return; }
            sessionStorage.setItem(chave, JSON.stringify({salvo: Date.now(), campos}));
            this.avisar(tipo, 'Rascunho salvo nesta aba. Fotos precisam ser selecionadas novamente após recarregar.');
        } catch (_) { this.avisar(tipo, 'Este navegador não permitiu salvar o rascunho. Mantenha o formulário aberto.'); }
    },
    restaurar(tipo) {
        if (this.editando(tipo)) return;
        const chave = this.chave(tipo); if (!chave) return;
        try {
            const texto = sessionStorage.getItem(chave); if (!texto) return;
            const data = JSON.parse(texto);
            if (!Number.isFinite(data.salvo) || Date.now() - data.salvo > this.ttl || !data.campos || typeof data.campos !== 'object') { sessionStorage.removeItem(chave); return; }
            for (const id of this.formularios[tipo]) {
                const campo = document.getElementById(id); const valor = data.campos[id];
                if (campo && typeof valor === 'string') {
                    if (campo.tagName === 'SELECT' && !Array.from(campo.options).some(o => o.value === valor)) continue;
                    campo.value = valor.slice(0, 4000);
                }
            }
            this.avisar(tipo,'Rascunho recuperado. Confira os dados antes de enviar.');
        } catch (_) { this.avisar(tipo,'Não foi possível recuperar o rascunho.'); }
    },
    limpar(tipo) {
        try { const chave = this.chave(tipo); if (chave) sessionStorage.removeItem(chave); } catch (_) {}
        this.avisar(tipo, '');
    },
    descartar(tipo) {
        if (this.editando(tipo) || !window.confirm('Descartar o texto deste rascunho?')) return;
        this.limpar(tipo);
        for (const id of this.formularios[tipo]) {
            const campo = document.getElementById(id);
            if (campo && !['SELECT'].includes(campo.tagName) && !['formItemData','alunoItemData'].includes(id)) campo.value = '';
        }
        this.avisar(tipo,'Rascunho descartado.');
    },
    limparConta() {
        for (const [tipo, ids] of Object.entries(this.formularios)) {
            this.limpar(tipo);
            document.getElementById(ids[0])?.closest('form')?.reset();
        }
        if (typeof fotosAlunoSelecionadas !== 'undefined') fotosAlunoSelecionadas = [];
        if (typeof UploadAluno !== 'undefined') UploadAluno.limpar();
        if (typeof UploadSecretaria !== 'undefined') UploadSecretaria.limpar();
        if (typeof CentralAvisos !== 'undefined') { CentralAvisos.itens = []; CentralAvisos.sessao = null; CentralAvisos.renderizar(); document.getElementById('badgeAvisos').hidden = true; }
        if (typeof MeusCadastros !== 'undefined') { MeusCadastros.itens = []; MeusCadastros.sessao = null; document.getElementById('listaMeusCadastros').replaceChildren(); }
    },
    iniciar() {
        for (const [tipo, ids] of Object.entries(this.formularios)) {
            const primeiro = document.getElementById(ids[0]); if (!primeiro) continue;
            const form = primeiro.closest('form');
            const bloco = document.createElement('div'); bloco.className = 'rascunho-controles';
            const status = document.createElement('p'); status.id = 'rascunho-' + tipo; status.setAttribute('role','status');
            status.textContent = 'O texto é preservado nesta aba por até 24 horas, até você sair da conta.';
            const btn = document.createElement('button'); btn.type = 'button'; btn.textContent = 'Descartar rascunho';
            btn.addEventListener('click', () => this.descartar(tipo)); bloco.append(status,btn); form.prepend(bloco);
            for (const id of ids) {
                const campo = document.getElementById(id);
                for (const evento of ['input','change']) campo.addEventListener(evento, () => this.salvar(tipo));
            }
        }
    }
};
document.addEventListener('DOMContentLoaded', () => Rascunhos.iniciar());
