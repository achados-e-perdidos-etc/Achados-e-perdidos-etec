// Os controles de autorização são exclusivos da secretaria titular.
async function verificarSessaoPainel() {
    try {
        const res = await fetch(`${API_URL}/api/auth/verificar`, {headers: getAuthHeadersGet()});
        const data = await res.json();
        if (!res.ok || !data.success || data.user.role !== 'secretaria') throw Error('Acesso não autorizado.');
        document.getElementById('menuAba-professores').classList.toggle('hidden', !!data.user.acesso_delegado);
        return true;
    } catch (error) {
        document.getElementById('menuAba-professores').classList.add('hidden');
        document.getElementById('loginScreen').classList.remove('hidden');
        localStorage.removeItem('secretaria_token');
        sessionStorage.removeItem('secretaria_token');
        mostrarToast('Sua sessão não tem acesso ao painel. Entre novamente.');
        return false;
    }
}

async function carregarSolicitacoesProfessores() {
    const lista = document.getElementById('listaAcessosProfessores');
    lista.replaceChildren();
    const aviso = document.createElement('p');
    aviso.textContent = 'Carregando solicitações...';
    lista.append(aviso);
    try {
        const res = await fetch(`${API_URL}/api/secretaria/professores`, {headers: getAuthHeadersGet()});
        const data = await res.json();
        if (!res.ok || !data.success) throw Error(data.message || 'Falha ao consultar solicitações.');
        lista.replaceChildren();
        if (!data.solicitacoes.length) {
            aviso.textContent = 'Nenhum professor solicitou acesso ainda.';
            lista.append(aviso);
        }
        const status = {PENDENTE: 'Aguardando aprovação', APROVADO: 'Acesso aprovado', RECUSADO: 'Recusado', REVOGADO: 'Revogado'};
        for (const pessoa of data.solicitacoes) {
            const card = document.createElement('div');
            card.className = 'card-dash';
            const nome = document.createElement('strong');
            nome.textContent = pessoa.nome;
            const email = document.createElement('p');
            email.textContent = pessoa.email;
            const situacao = document.createElement('p');
            situacao.textContent = status[pessoa.status] || pessoa.status;
            card.append(nome, email, situacao);
            const acoes = pessoa.status === 'PENDENTE' ? [['APROVAR', 'Aprovar'], ['RECUSAR', 'Recusar']] :
                pessoa.status === 'APROVADO' ? [['REVOGAR', 'Revogar acesso']] : [];
            for (const [acao, label] of acoes) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn-novo-item';
                btn.textContent = label;
                btn.addEventListener('click', () => decidirAcessoProfessor(pessoa.email, acao, btn));
                card.append(btn);
            }
            lista.append(card);
        }
    } catch (error) {
        lista.replaceChildren(aviso);
        aviso.textContent = error.message || 'Não foi possível carregar as solicitações.';
    }
}

async function decidirAcessoProfessor(email, acao, btn) {
    const pergunta = acao === 'APROVAR' ? `Autorizar ${email} a operar o painel, incluindo editar e excluir itens?` :
        acao === 'REVOGAR' ? `Revogar o acesso de ${email}?` : `Recusar a solicitação de ${email}?`;
    if (!window.confirm(pergunta)) return;
    btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/secretaria/professores/${encodeURIComponent(email)}/acesso`, {
            method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify({acao})
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw Error(data.message || 'Não foi possível atualizar o acesso.');
        mostrarToast('Permissão atualizada.');
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível atualizar o acesso.');
    } finally {
        await carregarSolicitacoesProfessores();
    }
}
