/* Histórico privado; nenhum conteúdo recebido é interpretado como HTML. */
const CentralAvisos = {
    itens: [], ocupado: false, sessao: null,
    async carregar(mais = false) {
        const token = SessaoPortal.token();
        if (!token || this.ocupado) return;
        this.ocupado = true;
        const sessao = token;
        if (this.sessao !== sessao) { this.itens = []; this.sessao = sessao; this.renderizar(); document.getElementById('badgeAvisos').hidden = true; }
        const status = document.getElementById('statusAvisos');
        status.textContent = 'Buscando avisos…';
        try {
            const ultimo = this.itens.at(-1)?.id;
            const res = await fetch(`${API_URL}/api/notificacoes${mais && ultimo ? '?antes=' + ultimo : ''}`, {headers: {Authorization: `Bearer ${token}`}});
            const data = await res.json();
            if (SessaoPortal.token() !== sessao) return;
            if (!res.ok || !data.success || !Array.isArray(data.notificacoes)) throw Error();
            this.itens = mais ? [...this.itens, ...data.notificacoes] : data.notificacoes;
            const badge = document.getElementById('badgeAvisos');
            badge.textContent = data.nao_lidas > 99 ? '99+' : String(data.nao_lidas);
            badge.hidden = !data.nao_lidas;
            document.getElementById('btnCentralAvisos').setAttribute('aria-label', `Notificações: ${data.nao_lidas} não lidas`);
            document.getElementById('maisAvisos').hidden = !data.tem_mais;
            document.getElementById('lerTodosAvisos').disabled = !this.itens.length || !data.nao_lidas;
            status.textContent = this.itens.length ? '' : 'Você ainda não recebeu avisos. As novidades aparecerão aqui.';
            this.renderizar();
        } catch (_) {
            if (SessaoPortal.token() === sessao) status.textContent = 'Não foi possível atualizar. Use “Atualizar avisos” para tentar novamente.';
        } finally { this.ocupado = false; }
    },
    renderizar() {
        const lista = document.getElementById('listaAvisos'); lista.replaceChildren();
        for (const aviso of this.itens) {
            const li = document.createElement('li'); li.className = 'aviso-card';
            const btn = document.createElement('button'); btn.type = 'button';
            btn.className = 'aviso-abrir';
            const titulo = document.createElement('strong'); titulo.textContent = `${aviso.lida ? '' : '● '}${aviso.titulo}`;
            const corpo = document.createElement('span'); corpo.textContent = aviso.corpo;
            const data = document.createElement('small'); data.textContent = new Date(aviso.criada_em).toLocaleString('pt-BR');
            btn.append(titulo, corpo, data); btn.addEventListener('click', () => this.ler(aviso));
            li.append(btn); lista.append(li);
        }
    },
    async ler(aviso = null) {
        const btn = document.getElementById('lerTodosAvisos');
        if (btn.dataset.ocupado || !this.itens.length) return;
        btn.dataset.ocupado = 'true'; btn.disabled = true;
        const token = SessaoPortal.token();
        try {
            const res = await fetch(`${API_URL}/api/notificacoes/${aviso ? aviso.id + '/lida' : 'lidas'}`, {
                method: 'PUT', headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
                body: JSON.stringify({ate_id: this.itens[0].id})
            });
            if (!res.ok) throw Error();
            if (SessaoPortal.token() !== token) return;
            if (aviso) {
                this.fechar();
                if (aviso.evento === 'chat') { if (!chatAberto) alternarJanelaChat(); }
                else if (aviso.evento === 'cadastro') abrirPainelMeusItens();
                else mudarAba('catalogo');
            }
            await this.carregar();
        } catch (_) { mostrarToast('Não foi possível marcar o aviso. Tente novamente.', 'error'); }
        finally { delete btn.dataset.ocupado; btn.disabled = false; }
    },
    abrir() { document.getElementById('centralAvisos').classList.remove('hidden'); this.carregar(); },
    fechar() { document.getElementById('centralAvisos').classList.add('hidden'); }
};
document.addEventListener('DOMContentLoaded', () => {
    CentralAvisos.carregar();
    setInterval(() => { if (!document.hidden && SessaoPortal.token() && document.getElementById('centralAvisos').classList.contains('hidden')) CentralAvisos.carregar(); }, 60000);
});
