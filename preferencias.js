/* Preferências locais, limitadas e separadas por conta. Nunca guardam credenciais. */
const PreferenciasUI = {
    conta:null, painel:false, restaurando:false, dados:null,
    chave(){return 'etec_preferencias_v1:'+encodeURIComponent(this.conta||'');},
    vazias(){return {filtros:{},visual:'grade',buscas:[]};},
    filtrosValidos(f){
        const n={};if(!f||typeof f!=='object')return n;
        for(const [k,max] of [['q',120],['categoria',50],['status',30],['local',100],['inicio',10],['fim',10]])if(typeof f[k]==='string')n[k]=f[k].slice(0,max);
        for(const k of ['inicio','fim'])if(n[k]&&!/^\d{4}-\d{2}-\d{2}$/.test(n[k]))n[k]='';
        if(!['TODOS','DISPONÍVEL','SOLICITADO','ENTREGUE','PARA DOAÇÃO','DOAÇÃO FEITA','DOACOES'].includes(n.status))n.status='TODOS';
        return n;
    },
    ler(){
        try{const raw=localStorage.getItem(this.chave())||'null';if(raw.length>16384)return this.vazias();const d=JSON.parse(raw);if(!d||typeof d!=='object')return this.vazias();
            return {filtros:this.filtrosValidos(d.filtros),visual:d.visual==='lista'?'lista':'grade',buscas:Array.isArray(d.buscas)?d.buscas.slice(0,10).map(f=>this.filtrosValidos(f)):[]};
        }catch(_){return this.vazias();}
    },
    aviso(texto){const p=document.getElementById('preferenciasStatus');if(p)p.textContent=texto;},
    guardar(){
        if(!this.conta||this.restaurando)return false;
        try{localStorage.setItem(this.chave(),JSON.stringify(this.dados));return true;}
        catch(_){this.aviso('Suas escolhas valem nesta página. O navegador bloqueou o salvamento.');return false;}
    },
    atuais(){return this.painel?{...PainelParidade.filtros(),status:filtroStatusAtual}:CatalogoPortal.filtros();},
    lembrar(){if(!this.conta||this.restaurando)return;this.dados.filtros=this.filtrosValidos(this.atuais());this.guardar();},
    aplicar(f){
        this.restaurando=true;f=this.filtrosValidos(f);
        try{
            if(this.painel){
                for(const [k,id] of Object.entries({q:'inputBusca',categoria:'secFiltroCategoria',local:'secFiltroLocal',inicio:'secFiltroInicio',fim:'secFiltroFim'})){
                    const n=document.getElementById(id);if(n){if(n.tagName==='SELECT'&&f[k]&&![...n.options].some(o=>o.value===f[k])){const o=document.createElement('option');o.value=f[k];o.textContent=f[k];n.append(o);}n.value=f[k]||(k==='categoria'?'TODOS':'');}}
                aplicarFiltroStatus(f.status||'TODOS',null);
            }else{
                termoBusca=f.q||'';categoriaAtual=f.categoria||'TODOS';statusAtual=f.status==='DOACOES'?'TODOS':(f.status||'TODOS');
                document.getElementById('btnClearSearch')?.classList.toggle('hidden',!termoBusca);
                for(const [id,v] of Object.entries({searchInput:termoBusca,catalogoLocal:f.local||'',catalogoInicio:f.inicio||'',catalogoFim:f.fim||''})){const n=document.getElementById(id);if(n)n.value=v;}
                selecionarFiltroCategoria(categoriaAtual,categoriaAtual==='TODOS'?'Todas':categoriaAtual);selecionarFiltroStatus(statusAtual,statusAtual==='TODOS'?'TODOS OS STATUS':statusAtual);CatalogoPortal.agendar();
            }
        }finally{this.restaurando=false;}
    },
    visual(v){
        if(!['grade','lista'].includes(v))return;this.dados.visual=v;
        const grid=document.getElementById(this.painel?'gridItensContainer':'itemsGrid');if(grid)grid.classList.toggle('preferencia-lista',v==='lista');
        document.querySelectorAll('[data-lista-visual]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.listaVisual===v)));this.guardar();
    },
    salvarBusca(){
        const f=this.filtrosValidos(this.atuais());
        if(!Object.entries(f).some(([k,v])=>v&&(!(k==='status'||k==='categoria')||v!=='TODOS'))){this.aviso('Escolha uma palavra ou um filtro antes de salvar.');return;}
        if(this.dados.buscas.some(b=>JSON.stringify(b)===JSON.stringify(f))){this.aviso('Essa busca já está salva.');return;}
        if(this.dados.buscas.length>=10){this.aviso('Você já tem 10 buscas. Remova uma para salvar outra.');return;}
        this.dados.buscas.push(f);const ok=this.guardar();this.renderizarBuscas();if(ok)this.aviso('Busca salva neste navegador.');
    },
    renderizarBuscas(){
        const box=document.getElementById('buscasSalvasLista');if(!box)return;box.replaceChildren();
        if(!this.dados.buscas.length){const p=document.createElement('p');p.textContent='Salve uma busca para retomá-la com um toque.';box.append(p);}
        this.dados.buscas.forEach((f,i)=>{
            const linha=document.createElement('div');linha.className='busca-salva';const texto=[f.q,f.categoria!=='TODOS'?f.categoria:'',f.status!=='TODOS'?f.status:'',f.local,f.inicio,f.fim].filter(Boolean).join(' · ');
            const b=TemaUI.botao(texto||'Busca salva',()=>{this.aplicar(f);this.lembrar();this.aviso('Busca aplicada.');document.getElementById('searchInput')?.focus();});b.title=texto;
            const remover=TemaUI.botao('Remover',()=>{this.dados.buscas.splice(i,1);const ok=this.guardar();this.renderizarBuscas();if(ok)this.aviso('Busca removida.');});remover.setAttribute('aria-label','Remover busca '+texto);linha.append(b,remover);box.append(linha);
        });
    },
    entrar(email,painel=false){
        if(typeof email!=='string'||email.length>254||!email.includes('@'))return;
        const conta=(painel?'secretaria:':'portal:')+email.toLowerCase();if(this.conta===conta)return;
        this.conta=conta;this.painel=painel;this.dados=this.ler();this.aplicar(this.dados.filtros);this.visual(this.dados.visual);this.renderizarBuscas();
        document.getElementById('preferenciasListas')?.removeAttribute('hidden');
    },
    sair(){this.conta=null;this.dados=this.vazias();this.aplicar({});this.visual('grade');this.renderizarBuscas();document.getElementById('preferenciasListas')?.setAttribute('hidden','');},
    iniciar(){
        this.painel=!!document.getElementById('inputBusca');const alvo=this.painel?document.querySelector('.paridade-filtros'):document.querySelector('#catalogScreen>.glass-panel');if(!alvo)return;
        this.dados=this.vazias();const d=document.createElement('details');d.id='preferenciasListas';d.className='preferencias-listas';d.hidden=true;
        const summary=document.createElement('summary');summary.textContent=this.painel?'Preferências da lista':'Minhas buscas e preferências';d.append(summary);
        const intro=document.createElement('p');intro.textContent='Filtros e organização são lembrados por conta, neste navegador.';d.append(intro);
        const grupo=document.createElement('div');grupo.className='preferencia-opcoes';
        for(const [v,t] of [['grade','Cartões'],['lista','Lista compacta']]){const b=TemaUI.botao(t,()=>this.visual(v));b.dataset.listaVisual=v;grupo.append(b);}d.append(grupo);
        if(!this.painel){const save=TemaUI.botao('Salvar busca atual',()=>this.salvarBusca());save.id='salvarBuscaAtual';const box=document.createElement('div');box.id='buscasSalvasLista';d.append(save,box);}
        const limpar=TemaUI.botao('Limpar preferências desta conta',()=>{this.dados=this.vazias();this.aplicar({});this.visual('grade');this.renderizarBuscas();if(this.guardar())this.aviso('Filtros, organização e buscas salvas foram limpos.');});
        const status=document.createElement('p');status.id='preferenciasStatus';status.setAttribute('role','status');d.append(limpar,status);alvo.after(d);
        if(this.painel){const original=filtrarItensNaTela;filtrarItensNaTela=(...args)=>{original(...args);this.lembrar();};}
        else{
            const original=CatalogoPortal.agendar.bind(CatalogoPortal);CatalogoPortal.agendar=()=>{this.lembrar();original();};
            // A pesquisa local continua lembrada quando a PWA abre sem conexão.
            document.getElementById('searchInput').addEventListener('input',()=>this.lembrar());
            for(const nome of ['selecionarFiltroCategoria','selecionarFiltroStatus','limparBusca']){const fn=window[nome];window[nome]=(...args)=>{const valor=fn(...args);this.lembrar();return valor;};}
            if(typeof alunoSessao!=='undefined'&&alunoSessao)this.entrar(alunoSessao.email);
        }
    }
};

const AtalhosSecretaria = {
    ocupado:false,timer:null,ultima:0,
    async atualizar(){
        if(this.ocupado||!tokenSecretaria||document.hidden)return;this.ocupado=true;
        const token=tokenSecretaria,abort=new AbortController(),prazo=setTimeout(()=>abort.abort(),10000);
        try{const res=await fetch(API_URL+'/api/secretaria/resumo',{headers:getAuthHeadersGet(),signal:abort.signal}),data=await res.json();if(token!==tokenSecretaria)return;
            if(!res.ok||!data.success||!['pendentes','retiradas','mensagens'].every(k=>Number.isSafeInteger(data[k])&&data[k]>=0))throw Error();
            for(const k of ['pendentes','retiradas','mensagens'])document.getElementById('atalhoContagem-'+k).textContent=String(data[k]);
            this.ultima=Date.now();document.getElementById('atalhosStatus').textContent='Atualizado às '+new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})+'.';
        }catch(_){if(token!==tokenSecretaria)return;for(const k of ['pendentes','retiradas','mensagens'])document.getElementById('atalhoContagem-'+k).textContent='—';document.getElementById('atalhosStatus').textContent='Não foi possível atualizar. Tente novamente.';}
        finally{clearTimeout(prazo);this.ocupado=false;}
    },
    abrir(aba){
        if(aba==='pendentes'){ModeracaoUI.estado='PENDENTE';document.getElementById('moderacaoEstado').value='PENDENTE';}
        if(aba==='itens'){aplicarFiltroStatus('SOLICITADO',null);document.getElementById('inputBusca').value='';for(const id of ['secFiltroLocal','secFiltroInicio','secFiltroFim'])document.getElementById(id).value='';document.getElementById('secFiltroCategoria').value='TODOS';filtrarItensNaTela();}
        if(aba==='chat'){document.getElementById('inputFiltroAlunosChat').value='';}
        trocarAba(aba);document.getElementById('secao-'+aba)?.scrollIntoView({block:'start',behavior:'instant'});
    },
    iniciar(){
        const sec=document.getElementById('secao-itens');if(!sec)return;
        const box=document.createElement('section');box.className='secretaria-atalhos';box.setAttribute('aria-label','Prioridades da secretaria');
        for(const [k,t,aba] of [['pendentes','Cadastros para analisar','pendentes'],['retiradas','Retiradas solicitadas','itens'],['mensagens','Mensagens não lidas','chat']]){
            const b=TemaUI.botao('',()=>this.abrir(aba));const n=document.createElement('strong');n.id='atalhoContagem-'+k;n.textContent='—';const label=document.createElement('span');label.textContent=t;b.append(n,label);box.append(b);}
        const footer=document.createElement('div');footer.className='atalhos-rodape';const p=document.createElement('span');p.id='atalhosStatus';p.textContent='Entre para consultar as prioridades.';footer.append(p,TemaUI.botao('Atualizar atalhos',()=>this.atualizar()));box.append(footer);sec.before(box);
        const original=verificarSessaoPainel;verificarSessaoPainel=async()=>{const ok=await original();if(ok){this.atualizar();clearInterval(this.timer);this.timer=setInterval(()=>this.atualizar(),60000);}return ok;};
        // Mutações e leitura de mensagens atualizam a mesma contagem, sem uma nova fila de polling.
        for(const nome of ['carregarItensSecretaria']){const fn=window[nome];if(typeof fn==='function')window[nome]=async(...args)=>{await fn(...args);this.atualizar();};}
        const conversas=renderizarListaConversasChat;renderizarListaConversasChat=()=>{conversas();document.getElementById('atalhoContagem-mensagens').textContent=String(listaConversasCache.reduce((s,c)=>s+(Number(c.nao_lidas)||0),0));};
        const mod=ModeracaoUI.carregar.bind(ModeracaoUI);ModeracaoUI.carregar=async(...args)=>{await mod(...args);this.atualizar();};
    }
};
document.addEventListener('DOMContentLoaded',()=>{PreferenciasUI.iniciar();AtalhosSecretaria.iniciar();});
