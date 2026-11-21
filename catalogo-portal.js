/* Busca paginada; resultados antigos nunca substituem uma pesquisa nova. */
const CatalogoPortal = {
    ativo:false, ocupado:false, geracao:0, proximo:null, teto:null, mais:false, abort:null, timer:null, observer:null,
    normalizar(value){return String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();},
    filtros(){return {q:termoBusca,categoria:categoriaAtual,status:statusAtual,local:document.getElementById('catalogoLocal')?.value.trim()||'',inicio:document.getElementById('catalogoInicio')?.value||'',fim:document.getElementById('catalogoFim')?.value||''};},
    corresponde(item){
        const f=this.filtros(),txt=this.normalizar([item.nome,item.txt_descricao,item.txt_local].join(' '));
        const cat=this.normalizar(item.categoria),local=this.normalizar(item.txt_local),date=this.dataISO(item.txt_data);
        return (f.categoria==='TODOS'||cat===this.normalizar(f.categoria))&&(f.status==='TODOS'||normalizarStatus(item)===f.status)
            &&this.normalizar(f.q).split(/\s+/).filter(Boolean).every(t=>txt.includes(t))&&local.includes(this.normalizar(f.local))
            &&(!f.inicio||(date&&date>=f.inicio))&&(!f.fim||(date&&date<=f.fim));
    },
    dataISO(value){const s=String(value||'');if(/^\d{4}-\d{2}-\d{2}$/.test(s))return s;const m=s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);return m?`${m[3]}-${m[2]}-${m[1]}`:null;},
    status(text,erro=false){const n=document.getElementById('catalogoStatus');if(n){n.textContent=text;n.classList.toggle('catalogo-erro',erro);}},
    botoes(){const b=document.getElementById('catalogoMais');if(b){b.hidden=!this.mais;b.disabled=this.ocupado;b.textContent=this.ocupado?'Carregando…':'Carregar mais objetos';}},
    cache(){
        try{const raw=JSON.parse(localStorage.getItem('cache_catalogo_v2')||'null');if(raw&&Array.isArray(raw.itens))return raw;
            const antigo=JSON.parse(localStorage.getItem('cache_itens_etec')||'[]');return Array.isArray(antigo)&&antigo.length?{itens:antigo.slice(0,96),em:null}:null;
        }catch(_){return null;}
    },
    guardar(){try{localStorage.setItem('cache_catalogo_v2',JSON.stringify({itens:todosItens.slice(0,96),em:Date.now()}));localStorage.removeItem('cache_itens_etec');}catch(_){}},
    agendar(){
        clearTimeout(this.timer);this.geracao++;this.abort?.abort();this.ocupado=true;this.botoes();this.resumoFiltros();
        this.timer=setTimeout(()=>this.carregar(false),250);
    },
    async carregar(mais=false){
        clearTimeout(this.timer);
        if(mais&&(this.ocupado||!this.mais))return;
        const g=++this.geracao;this.abort?.abort();this.abort=new AbortController();this.ocupado=true;this.botoes();document.getElementById('itemsGrid')?.setAttribute('aria-busy','true');this.resumoFiltros();
        if(!mais){this.proximo=null;this.teto=null;this.mais=false;}
        if(!navigator.onLine){
            if(!mais){const cache=this.cache();todosItens=cache?.itens||[];renderizarItens(true);}
            this.status('Sem conexão: os filtros consideram apenas os objetos guardados neste dispositivo.');this.ocupado=false;this.botoes();document.getElementById('itemsGrid')?.setAttribute('aria-busy','false');document.getElementById('loadingOverlay')?.classList.add('fade-out');this.resumoFiltros();return false;
        }
        this.status(mais?'Carregando mais objetos…':'Buscando objetos…');
        let temporizou=false;const prazo=setTimeout(()=>{if(g===this.geracao){temporizou=true;this.abort.abort();}},15000);
        try{
            const params=new URLSearchParams({...this.filtros(),limite:'24'});
            if(mais&&this.proximo){params.set('antes',this.proximo);if(this.teto)params.set('teto',this.teto);}
            const res=await fetch(API_URL+'/api/catalogo?'+params,{signal:this.abort.signal});const data=await res.json();
            if(g!==this.geracao)return;
            if(!res.ok||!data.success||!Array.isArray(data.itens))throw Error(data.message||'Não foi possível carregar o catálogo.');
            this.ativo=true;this.proximo=data.proximo;this.teto=data.teto;this.mais=data.tem_mais===true;
            todosItens=mais?[...new Map([...todosItens,...data.itens].map(item=>[item.id,item])).values()]:data.itens;
            renderizarItens(true);this.guardar();
            this.status(todosItens.length?`${todosItens.length} objetos carregados${this.mais?'. Há mais resultados abaixo.':'. Você chegou ao fim desta busca.'}`:'Nenhum objeto corresponde aos filtros.');
            return true;
        }catch(error){
            if(g!==this.geracao||(error.name==='AbortError'&&!temporizou))return;
            if(temporizou)error=Error('A consulta demorou mais que o esperado.');
            if(!mais&&!todosItens.length){const cache=this.cache();if(cache){todosItens=cache.itens;renderizarItens(true);}}
            this.status((error.message||'A conexão falhou.')+' Use Atualizar catálogo para tentar novamente. Dados guardados podem estar desatualizados.',true);return false;
        }finally{
            clearTimeout(prazo);
            if(g===this.geracao){this.ocupado=false;this.botoes();document.getElementById('itemsGrid')?.setAttribute('aria-busy','false');document.getElementById('loadingOverlay')?.classList.add('fade-out');}
        }
    },
    imagens(){
        this.observer?.disconnect();
        const imgs=document.querySelectorAll('#itemsGrid img[data-src]');
        const abrir=img=>{const src=urlImagemSegura(img.dataset.src);img.removeAttribute('data-src');if(!src)return;
            img.onload=()=>img.classList.add('catalogo-imagem-pronta');img.onerror=()=>{img.removeAttribute('src');img.alt='Foto indisponível. Abra o objeto para conferir os detalhes.';};img.src=src;};
        if(!('IntersectionObserver' in window)){imgs.forEach(abrir);return;}
        this.observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){this.observer.unobserve(entry.target);abrir(entry.target);}},{rootMargin:'0px',threshold:.01});
        imgs.forEach(img=>this.observer.observe(img));
    },
    resumoFiltros(){
        const box=document.getElementById('catalogoFiltrosAtivos');if(!box)return;box.replaceChildren();
        const f=this.filtros();
        const filtros=[['q','Busca: '+f.q,!!f.q],['categoria',f.categoria,f.categoria!=='TODOS'],['status',f.status,f.status!=='TODOS'],['local','Local: '+f.local,!!f.local],['inicio','A partir de '+f.inicio,!!f.inicio],['fim','Até '+f.fim,!!f.fim]];
        for(const [key,label,ativo] of filtros){
            if(!ativo)continue;const b=document.createElement('button');b.type='button';b.className='ux-filter-chip';
            b.textContent=label+' ×';b.setAttribute('aria-label','Remover filtro '+label);
            b.onclick=()=>{if(key==='q')limparBusca();else if(key==='categoria')selecionarFiltroCategoria('TODOS','Todas');else if(key==='status')selecionarFiltroStatus('TODOS','TODOS OS STATUS');else{document.getElementById({local:'catalogoLocal',inicio:'catalogoInicio',fim:'catalogoFim'}[key]).value='';this.agendar();}};box.append(b);
        }
        box.hidden=!box.childElementCount;
    },
    limpar(){for(const id of ['catalogoLocal','catalogoInicio','catalogoFim']){const n=document.getElementById(id);if(n)n.value='';}selecionarFiltroCategoria('TODOS','Todas');selecionarFiltroStatus('TODOS','TODOS OS STATUS');limparBusca();},
    iniciar(){
        const grid=document.getElementById('itemsGrid');if(!grid)return;
        const box=document.createElement('details');box.className='catalogo-filtros';box.innerHTML='<summary>Local e período</summary><div class="catalogo-campos"><label>Local encontrado<input id="catalogoLocal" type="search" maxlength="100" placeholder="Ex: Pátio ou Biblioteca"></label><label>Encontrado a partir de<input id="catalogoInicio" type="date"></label><label>Encontrado até<input id="catalogoFim" type="date"></label></div><button class="ev-action" type="button" id="catalogoLimpar">Limpar todos os filtros</button>';
        const controls=document.querySelector('#catalogScreen > .glass-panel');controls.append(box);
        const ativos=document.createElement('div');ativos.id='catalogoFiltrosAtivos';ativos.className='ux-filter-chips';ativos.setAttribute('aria-label','Filtros aplicados');ativos.hidden=true;controls.append(ativos);
        for(const id of ['catalogoLocal','catalogoInicio','catalogoFim'])document.getElementById(id).addEventListener('input',()=>this.agendar());
        document.getElementById('catalogoLimpar').onclick=()=>this.limpar();
        const status=document.createElement('p');status.id='catalogoStatus';status.className='catalogo-status';status.setAttribute('role','status');grid.before(status);
        const actions=document.createElement('div');actions.className='catalogo-acoes';
        const more=document.createElement('button');more.id='catalogoMais';more.type='button';more.className='ev-action';more.textContent='Carregar mais objetos';more.hidden=true;more.onclick=()=>this.carregar(true);
        const refresh=document.createElement('button');refresh.type='button';refresh.className='ev-action';refresh.textContent='Atualizar catálogo';refresh.onclick=()=>this.carregar(false);actions.append(more,refresh);grid.after(actions);
    }
};
document.addEventListener('DOMContentLoaded',()=>CatalogoPortal.iniciar());
