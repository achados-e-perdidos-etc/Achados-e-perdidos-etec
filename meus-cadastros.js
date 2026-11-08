const MeusCadastros = {
    itens: [], ocupado: false, sessao: null,
    async carregar(mais = false) {
        if (this.ocupado || !SessaoPortal.token()) return;
        this.ocupado = true;
        const token = SessaoPortal.token();
        if (!mais || this.sessao !== token) { this.itens = []; this.sessao = token; }
        const status = document.getElementById('statusMeusCadastros');
        const lista = document.getElementById('listaMeusCadastros');
        status.textContent = 'Buscando seus cadastros…';
        try {
            const ultimo = this.itens.at(-1)?.id;
            const res = await fetch(`${API_URL}/api/itens/cadastrados-por-mim${mais && ultimo ? '?antes=' + ultimo : ''}`, {headers: {Authorization: `Bearer ${token}`}});
            const data = await res.json();
            if (SessaoPortal.token() !== token) return;
            if (!res.ok || !data.success) throw Error();
            this.itens.push(...data.cadastros); lista.replaceChildren();
            const labels = {AGUARDANDO:'Aguardando aprovação',PUBLICADO:'Publicado no catálogo',RECUSADO:'Cadastro recusado',ENTREGUE:'Entregue ao responsável',DOADO:'Doação concluída',REMOVIDO:'Removido pela secretaria','PARA DOAÇÃO':'Aguardando doação'};
            for (const item of this.itens) {
                const card = document.createElement('article'); card.className = 'cadastro-card';
                const titulo = document.createElement('h4'); titulo.textContent = item.nome;
                const estado = document.createElement('strong'); estado.textContent = labels[item.situacao] || 'Em análise';
                const data = document.createElement('p'); data.textContent = `Enviado em ${new Date(item.enviado_em).toLocaleString('pt-BR')} · ${item.categoria}`;
                card.append(titulo,estado,data);
                if(item.motivo_recusa){const motivo=document.createElement('p');motivo.className='mod-motivo';motivo.textContent='Orientação: '+item.motivo_recusa;card.append(motivo);}
                if(item.situacao==='RECUSADO'&&item.item_id){const corrigir=document.createElement('button');corrigir.type='button';corrigir.className='ev-action';corrigir.textContent='Corrigir e reenviar';corrigir.onclick=()=>CorrecaoCadastro.abrir(item.item_id);card.append(corrigir);}
                lista.append(card);
            }
            status.textContent = this.itens.length ? '' : 'Você ainda não tem cadastros com autoria registrada. Os próximos objetos enviados aparecerão aqui.';
            document.getElementById('maisCadastros').hidden = !data.tem_mais;
        } catch (_) { status.textContent = 'Não foi possível carregar. Use “Atualizar cadastros” para tentar novamente.'; }
        finally { this.ocupado = false; }
    }
};
