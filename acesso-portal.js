// A senha nunca é armazenada. Persistência exige uma escolha explícita.
const SessaoPortal = {
    migrarLegado() {
        const legado = localStorage.getItem('aluno_token');
        if (!legado || localStorage.getItem('aluno_lembrar') === 'true') return;
        if (!sessionStorage.getItem('aluno_token')) {
            sessionStorage.setItem('aluno_token', legado);
            const dados = localStorage.getItem('aluno_dados');
            if (dados) sessionStorage.setItem('aluno_dados', dados);
        }
        if (localStorage.getItem('secretaria_token') === legado) {
            if (sessionStorage.getItem('aluno_token') === legado) sessionStorage.setItem('secretaria_token', legado);
            localStorage.removeItem('secretaria_token');
        }
        localStorage.removeItem('aluno_token');
        localStorage.removeItem('aluno_dados');
    },
    token() {
        this.migrarLegado();
        return sessionStorage.getItem('aluno_token') || localStorage.getItem('aluno_token');
    },
    dados() {
        this.migrarLegado();
        try {
            const origem = sessionStorage.getItem('aluno_token') ? sessionStorage : localStorage;
            const dados = JSON.parse(origem.getItem('aluno_dados') || 'null');
            return dados && typeof dados.nome === 'string' && typeof dados.email === 'string' ? dados : null;
        } catch (error) { return null; }
    },
    salvar(token, dados, lembrar = false) {
        if (typeof token !== 'string' || !token.trim() || !dados
            || typeof dados.nome !== 'string' || typeof dados.email !== 'string') throw Error('Resposta de acesso inválida.');
        this.limpar();
        const destino = lembrar ? localStorage : sessionStorage;
        destino.setItem('aluno_token', token.trim());
        destino.setItem('aluno_dados', JSON.stringify(dados));
        if (lembrar) localStorage.setItem('aluno_lembrar', 'true');
    },
    limpar() {
        for (const destino of [sessionStorage, localStorage]) {
            for (const chave of ['aluno_token', 'aluno_dados', 'aluno_lembrar', 'secretaria_token']) destino.removeItem(chave);
        }
    },
    compartilharPainel() {
        const token = this.token();
        if (!token) return;
        sessionStorage.removeItem('secretaria_token');
        localStorage.removeItem('secretaria_token');
        const destino = localStorage.getItem('aluno_lembrar') === 'true' && localStorage.getItem('aluno_token') === token
            ? localStorage : sessionStorage;
        destino.setItem('secretaria_token', token);
    }
};

let authOcupada = false;
let focoAntesAuth = null;

function iniciarAnimacaoAuth(modo) {
    if (authOcupada) return false;
    authOcupada = true;
    focoAntesAuth = document.activeElement;
    const camada = document.getElementById('authTransition');
    camada.dataset.estado = 'carregando';
    document.getElementById('authTransitionTitulo').textContent = modo === 'cadastro' ? 'Preparando seu espaço' : 'Seu portal está logo ali';
    document.getElementById('authTransitionTexto').textContent = modo === 'cadastro' ? 'Criando sua conta para conectar o que foi perdido a quem procura.' : 'Conferindo seus dados para abrir seu portal.';
    document.getElementById('authTransitionEtapa').textContent = modo === 'cadastro' ? 'Criando sua conta' : 'Conectando você';
    document.getElementById('loginAuthCard').setAttribute('aria-busy', 'true');
    document.querySelectorAll('#loginAlunoScreen form').forEach(form => { form.inert = true; });
    camada.hidden = false;
    camada.focus({preventScroll: true});
    return true;
}

async function confirmarAnimacaoAuth(modo) {
    document.getElementById('authTransition').dataset.estado = 'sucesso';
    document.getElementById('authTransitionTitulo').textContent = modo === 'cadastro' ? 'Sua conta está pronta!' : 'Bem-vindo de volta!';
    document.getElementById('authTransitionTexto').textContent = 'Vamos encontrar o que é seu.';
    document.getElementById('authTransitionEtapa').textContent = 'Acesso confirmado';
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        await new Promise(resolve => setTimeout(resolve, 450));
    }
}

function encerrarAnimacaoAuth(sucesso = false) {
    document.getElementById('authTransition').hidden = true;
    document.getElementById('loginAuthCard').setAttribute('aria-busy', 'false');
    document.querySelectorAll('#loginAlunoScreen form').forEach(form => { form.inert = false; });
    authOcupada = false;
    if (!sucesso && focoAntesAuth?.isConnected) focoAntesAuth.focus({preventScroll: true});
}
