/* Acompanhar o aparelho depende de uma escolha explícita da pessoa. */
const TemaUI = {
    chave:'etec_aparencia_v1', escolha:null, media:window.matchMedia('(prefers-color-scheme: dark)'),
    ler(){try{return localStorage.getItem(this.chave);}catch(_){return null;}},
    aplicar(){
        const escuro=this.escolha!=='claro'&&(this.escolha!=='sistema'||this.media.matches);
        document.documentElement.dataset.tema=escuro?'escuro':'claro';
        document.documentElement.style.colorScheme=escuro?'dark':'light';
        if(document.body){document.body.classList.toggle('dark-theme',escuro);document.body.classList.toggle('light-theme',!escuro);}
        if(typeof Chart!=='undefined'){
            const cor=escuro?'#c4cfdf':'#4b5b70';Chart.defaults.color=cor;
            for(const chart of Object.values(Chart.instances)){
                if(chart.options.plugins?.legend?.labels)chart.options.plugins.legend.labels.color=cor;
                for(const scale of Object.values(chart.options.scales||{})){if(scale.ticks)scale.ticks.color=cor;}
                chart.update('none');
            }
        }
    },
    escolher(valor){
        if(!['claro','escuro','sistema'].includes(valor))return;
        this.escolha=valor;let salvo=true;
        try{localStorage.setItem(this.chave,valor);}catch(_){salvo=false;}
        this.aplicar();document.querySelectorAll('.tema-pergunta').forEach(n=>n.remove());
        document.dispatchEvent(new CustomEvent('etec:tema',{detail:valor}));
        return salvo;
    },
    botao(texto,fn){const b=document.createElement('button');b.type='button';b.className='preferencia-botao';b.textContent=texto;if(texto)b.setAttribute('aria-label',texto);b.onclick=fn;return b;},
    abrir(){
        if(document.getElementById('aparenciaDialog')?.open)return;
        const d=document.createElement('dialog');d.id='aparenciaDialog';d.className='preferencia-dialog';d.setAttribute('aria-labelledby','aparenciaTitulo');
        const h=document.createElement('h2');h.id='aparenciaTitulo';h.textContent='Do seu jeito';
        const p=document.createElement('p');p.textContent='Escolha a aparência. Automático acompanha o modo claro ou escuro do seu aparelho.';
        const status=document.createElement('p');status.setAttribute('role','status');
        const grupo=document.createElement('div');grupo.className='preferencia-opcoes';
        for(const [v,t] of [['claro','Claro'],['escuro','Escuro'],['sistema','Automático · usar o sistema']]){
            const b=this.botao(t,()=>{const salvo=this.escolher(v);grupo.querySelectorAll('button').forEach(n=>n.setAttribute('aria-pressed',String(n===b)));status.textContent=salvo?'Preferência salva neste navegador.':'Aparência aplicada nesta página. O navegador bloqueou o salvamento.';});
            b.setAttribute('aria-pressed',String(this.escolha===v));grupo.append(b);
        }
        d.append(h,p,grupo,status,this.botao('Concluir',()=>d.close()));document.body.append(d);d.addEventListener('close',()=>d.remove(),{once:true});d.showModal();
    },
    iniciar(){
        this.aplicar();
        for(const pai of [document.querySelector('.glass-header>.max-w-5xl'),document.getElementById('perfilMenu'),document.querySelector('.header-direita-botoes'),document.getElementById('loginAuthCard'),document.querySelector('.login-card')].filter(Boolean)){
            const b=this.botao('Aparência',()=>this.abrir());b.classList.add('tema-abrir');b.setAttribute('aria-label','Escolher aparência do site');pai.append(b);
        }
        if(!this.escolha){
            const n=document.createElement('aside');n.className='tema-pergunta';n.setAttribute('aria-label','Preferência de aparência');
            const titulo=document.createElement('strong');titulo.textContent='Uma aparência confortável para você';const p=document.createElement('p');p.textContent='Quer que o site acompanhe o tema claro ou escuro do seu aparelho?';
            const acoes=document.createElement('div');acoes.className='preferencia-opcoes';
            for(const [v,t] of [['sistema','Sim, usar o sistema'],['claro','Prefiro claro'],['escuro','Prefiro escuro']])acoes.append(this.botao(t,()=>this.escolher(v)));
            n.append(titulo,p,acoes);const lugar=document.querySelector('main');if(lugar)lugar.prepend(n);else document.body.append(n);
            // O convite também está no acesso; as duas cópias compartilham a escolha.
            const login=document.getElementById('loginAuthCard')||document.querySelector('.login-card');
            if(login){const copy=n.cloneNode(true);[...copy.querySelectorAll('button')].forEach((b,i)=>b.onclick=()=>this.escolher(['sistema','claro','escuro'][i]));login.append(copy);}
        }
    }
};
TemaUI.escolha=['claro','escuro','sistema'].includes(TemaUI.ler())?TemaUI.ler():null;
TemaUI.aplicar();
TemaUI.media.addEventListener('change',()=>{if(TemaUI.escolha==='sistema')TemaUI.aplicar();});
window.addEventListener('storage',e=>{if(e.key===TemaUI.chave){TemaUI.escolha=['claro','escuro','sistema'].includes(e.newValue)?e.newValue:null;TemaUI.aplicar();if(TemaUI.escolha)document.querySelectorAll('.tema-pergunta').forEach(n=>n.remove());}});
document.addEventListener('DOMContentLoaded',()=>TemaUI.iniciar());
