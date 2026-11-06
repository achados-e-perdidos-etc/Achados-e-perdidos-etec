// Portal do professor: a autorização é sempre consultada no servidor.
function contaDeProfessor() {
    return !!alunoSessao && /@(etec|cps)\.sp\.gov\.br$/i.test(alunoSessao.email || '');
}

async function atualizarAcessoProfessor() {
    const area = document.getElementById('acessoProfessor');
    if (!area) return null;
    area.classList.toggle('hidden', !contaDeProfessor());
    if (!contaDeProfessor()) return null;
    const texto = document.getElementById('statusAcessoProfessor');
    const solicitar = document.getElementById('btnSolicitarAcessoProfessor');
    const abrir = document.getElementById('btnAbrirPainelProfessor');
    solicitar.disabled = true;
    abrir.classList.add('hidden');
    try {
        const res = await fetch(`${API_URL}/api/professores/acesso`, {
            headers: {Authorization: `Bearer ${localStorage.getItem('aluno_token') || ''}`}
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw Error(data.message || 'Falha na consulta.');
        const mensagens = {
            NAO_SOLICITADO: 'Solicite autorização para ajudar no atendimento e no gerenciamento de itens.',
            PENDENTE: 'Sua solicitação aguarda a decisão da secretaria.',
            APROVADO: 'Acesso aprovado. Você já pode ajudar pelo painel da secretaria.',
            RECUSADO: 'A solicitação foi recusada. Você pode solicitar novamente.',
            REVOGADO: 'Seu acesso foi revogado. Você pode solicitar novamente.'
        };
        texto.textContent = mensagens[data.status] || 'Consulte a secretaria sobre sua solicitação.';
        solicitar.classList.toggle('hidden', data.status === 'APROVADO');
        solicitar.disabled = !['NAO_SOLICITADO', 'RECUSADO', 'REVOGADO'].includes(data.status);
        abrir.classList.toggle('hidden', data.status !== 'APROVADO');
        return data.status;
    } catch (error) {
        texto.textContent = 'Não foi possível consultar seu acesso. Atualize o status para tentar novamente.';
        return null;
    }
}

async function solicitarAcessoProfessor() {
    const btn = document.getElementById('btnSolicitarAcessoProfessor');
    btn.disabled = true;
    try {
        const res = await fetch(`${API_URL}/api/professores/acesso`, {
            method: 'POST', headers: {Authorization: `Bearer ${localStorage.getItem('aluno_token') || ''}`}
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw Error(data.message || 'Falha ao solicitar.');
        mostrarToast(data.status === 'APROVADO' ? 'Seu acesso já está aprovado.' : 'Solicitação enviada à secretaria.', 'success');
    } catch (error) {
        mostrarToast(error.message || 'Não foi possível solicitar o acesso.', 'error');
    } finally {
        await atualizarAcessoProfessor();
    }
}

async function abrirPainelProfessor() {
    if (await atualizarAcessoProfessor() !== 'APROVADO') return;
    const destino = new URL('/secretaria', API_URL);
    if (destino.origin !== window.location.origin) {
        mostrarToast('Entre pelo endereço principal do site para abrir o painel.', 'info');
        return;
    }
    localStorage.setItem('secretaria_token', localStorage.getItem('aluno_token'));
    window.location.assign(destino.href);
}
