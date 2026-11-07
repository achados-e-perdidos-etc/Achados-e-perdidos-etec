/* Fluxos pessoais e administrativos usam somente a sessão atual. */
const EvolucaoUI = {
    node(tag,text,className) { const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n; },
    dialog(title) {
        const previous=document.activeElement,d=document.createElement('dialog');d.className='evolucao-dialog';
        const close=this.node('button','×','ev-close');close.type='button';close.setAttribute('aria-label','Fechar');close.onclick=()=>d.close();
        const h=this.node('h2',title);h.id='ev-title-'+crypto.randomUUID();d.setAttribute('aria-labelledby',h.id);
        d.append(close,h);document.body.append(d);d.addEventListener('close',()=>{d.remove();if(previous?.isConnected)previous.focus();},{once:true});
        d.showModal();return d;
    },
    field(form,label,type='text') {
        const l=this.node('label',label,'ev-field'),input=document.createElement('input');input.type=type;if(type==='checkbox')l.classList.add('ev-check');l.append(input);form.append(l);return input;
    },
    token() { return typeof SessaoPortal!=='undefined'?SessaoPortal.token():typeof tokenSecretaria!=='undefined'?tokenSecretaria:null; },
    async request(path,body) {
        const token=this.token();if(!token)throw Error('Entre novamente para continuar.');
        const res=await fetch(API_URL+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
        const data=await res.json();if(token!==this.token())throw Error('A conta mudou. Reabra esta tela.');
        if(!res.ok||!data.success)throw Error(data.message||'Não foi possível concluir.');return data;
    }
};

const RetiradasAluno = {
    async mostrar(id) {
        const d=EvolucaoUI.dialog('Seu código de retirada'),status=EvolucaoUI.node('p','Preparando código…');status.setAttribute('role','status');d.append(status);
        try {
            const data=await EvolucaoUI.request('/api/retiradas/'+Number(id)+'/codigo',{});if(!d.isConnected)return;
            status.textContent='Objeto #'+data.item_id;
            const code=EvolucaoUI.node('div',data.codigo,'ev-code');code.setAttribute('aria-label','Código: '+data.codigo.split('').join(' '));d.append(code);
            d.append(EvolucaoUI.node('p','Válido até '+new Date(data.expira_em).toLocaleTimeString('pt-BR')+'. Se vencer, abra esta tela para obter outro.'));
            d.append(EvolucaoUI.node('p',data.aviso,'ev-note'));
        } catch(error){status.textContent=error.message;status.className='ev-error';}
    }
};

const RetiradaSecretaria = {
    abrir() {
        const d=EvolucaoUI.dialog('Confirmar retirada com código');
        d.append(EvolucaoUI.node('p','Confira o documento do aluno e detalhes particulares do objeto antes de confirmar. O código identifica a solicitação; não comprova a propriedade.','ev-note'));
        const form=document.createElement('form'),id=EvolucaoUI.field(form,'Número do objeto','number'),code=EvolucaoUI.field(form,'Código de seis dígitos');
        id.min=1;id.required=true;code.inputMode='numeric';code.pattern='[0-9]{6}';code.maxLength=6;code.required=true;code.autocomplete='off';
        const check=EvolucaoUI.field(form,'Conferi presencialmente a identidade e os detalhes do objeto','checkbox');check.required=true;
        form.append(EvolucaoUI.node('p','Assinatura do aluno: declaro que recebi o objeto indicado acima. Este registro é um comprovante simples de recebimento.'));
        const canvas=document.createElement('canvas');canvas.width=700;canvas.height=330;canvas.className='ev-signature';canvas.setAttribute('aria-label','Área para assinar com o dedo ou mouse');form.append(canvas);
        const ctx=canvas.getContext('2d');let drawing=false,drawn=false;
        const blank=()=>{ctx.fillStyle='white';ctx.fillRect(0,0,700,330);ctx.strokeStyle='#172033';ctx.lineWidth=3;ctx.lineCap='round';drawn=false;};blank();
        const point=e=>{const r=canvas.getBoundingClientRect();return [(e.clientX-r.left)*700/r.width,(e.clientY-r.top)*330/r.height];};
        canvas.onpointerdown=e=>{drawing=true;canvas.setPointerCapture(e.pointerId);ctx.beginPath();ctx.moveTo(...point(e));};
        canvas.onpointermove=e=>{if(!drawing)return;ctx.lineTo(...point(e));ctx.stroke();drawn=true;};
        canvas.onpointerup=canvas.onpointercancel=()=>{drawing=false;};
        const clear=EvolucaoUI.node('button','Limpar assinatura');clear.type='button';clear.onclick=blank;form.append(clear);
        const typed=EvolucaoUI.field(form,'Se não puder desenhar, digite o nome completo para registrar o aceite');typed.maxLength=100;
        const accept=EvolucaoUI.node('button','Usar nome digitado');accept.type='button';accept.onclick=()=>{
            if(typed.value.trim().length<5)return;
            blank();ctx.fillStyle='#172033';ctx.font='32px sans-serif';ctx.fillText('Aceite por nome digitado:',18,100);
            ctx.fillText(typed.value.trim(),18,190,660);drawn=true;
        };form.append(accept);
        const submit=EvolucaoUI.node('button','Confirmar entrega');submit.type='submit';form.append(submit);
        const status=EvolucaoUI.node('p','');status.setAttribute('role','status');form.append(status);d.append(form);
        let busy=false;const key=crypto.randomUUID();
        form.onsubmit=async e=>{
            e.preventDefault();if(busy)return;
            if(!drawn){status.textContent='Peça ao aluno para assinar na área branca.';return;}
            busy=true;submit.disabled=clear.disabled=accept.disabled=typed.disabled=true;status.textContent='Conferindo código e registrando a entrega…';
            const body={codigo:code.value,requisicao:key,identidade_conferida:check.checked,assinatura:canvas.toDataURL('image/png')};
            id.disabled=code.disabled=check.disabled=true;canvas.style.pointerEvents='none';
            try {
                const data=await EvolucaoUI.request('/api/retiradas/'+Number(id.value)+'/confirmar',body);
                if(!d.isConnected)return;
                status.textContent=data.message;submit.hidden=true;clear.disabled=true;
                id.disabled=code.disabled=check.disabled=true;canvas.style.pointerEvents='none';
                if(typeof carregarItensSecretaria==='function')carregarItensSecretaria();
            } catch(error){if(d.isConnected)status.textContent=error.message;}
            finally{busy=false;submit.disabled=false;if(!submit.hidden){id.disabled=code.disabled=check.disabled=clear.disabled=accept.disabled=typed.disabled=false;canvas.style.pointerEvents='';}}
        };
    },
    async verAssinatura(id) {
        const d=EvolucaoUI.dialog('Comprovante de recebimento'),status=EvolucaoUI.node('p','Carregando registro privado…');status.setAttribute('role','status');d.append(status);
        try{
            const token=EvolucaoUI.token(),res=await fetch(API_URL+'/api/retiradas/comprovantes/'+Number(id)+'/assinatura',{headers:{Authorization:'Bearer '+token}});
            if(!res.ok||res.headers.get('Content-Type')?.split(';')[0]!=='image/jpeg')throw Error('Registro indisponível ou sessão expirada.');
            const blob=await res.blob();if(!d.isConnected||token!==EvolucaoUI.token())return;
            const url=URL.createObjectURL(blob),img=document.createElement('img');img.src=url;img.alt='Assinatura ou aceite registrado no recebimento';img.style.width='100%';d.append(img);status.textContent='Acesso restrito à equipe autorizada.';
            d.addEventListener('close',()=>URL.revokeObjectURL(url),{once:true});
        }catch(error){status.textContent=error.message;}
    },
    historico() {
        const d=EvolucaoUI.dialog('Ocorrências do objeto'),form=document.createElement('form'),id=EvolucaoUI.field(form,'Número do objeto','number');id.min=1;id.required=true;
        const btn=EvolucaoUI.node('button','Consultar');btn.type='submit';form.append(btn);d.append(form);
        const status=EvolucaoUI.node('p','Somente a equipe autorizada pode consultar este histórico.');status.setAttribute('role','status');const list=document.createElement('div');d.append(status,list);
        const more=EvolucaoUI.node('button','Ver ocorrências anteriores');more.hidden=true;d.append(more);let last=null,active=null,busy=false;
        const load=async next=>{
            if(busy)return;busy=true;btn.disabled=more.disabled=true;
            if(!next){list.replaceChildren();last=null;active=Number(id.value);}
            status.textContent='Consultando…';
            try {
                const data=await EvolucaoUI.request('/api/itens/'+active+'/ocorrencias'+(next?'?antes='+last:''));if(!d.isConnected)return;
                for(const row of data.ocorrencias){const card=EvolucaoUI.node('article',undefined,'ev-log');
                    card.append(EvolucaoUI.node('strong',({INSERT:'Cadastro',UPDATE:'Alteração',DELETE:'Exclusão'})[row.acao]||row.acao));
                    const perfil=({administrador_geral:'Administração',moderador:'Moderação',aluno:'Aluno',sistema:'Automático'})[row.perfil]||row.perfil;
                    card.append(EvolucaoUI.node('p',row.ator_id+' · '+perfil+' · '+new Date(row.criada_em).toLocaleString('pt-BR')));
                    const descrever=valor=>valor ? [valor.status,valor.aprovado?'Aprovado':'Aguardando aprovação',valor.nome,valor.categoria,valor.local].filter(Boolean).join(' · ') : 'Sem registro';
                    card.append(EvolucaoUI.node('p','Antes: '+descrever(row.anterior)),EvolucaoUI.node('p','Depois: '+descrever(row.atual)));list.append(card);last=row.id;}
                status.textContent=list.children.length?'Histórico preservado, inclusive após excluir o objeto.':'Nenhuma ocorrência registrada para esse número.';more.hidden=!data.tem_mais;
            }catch(error){status.textContent=error.message;}
            finally{busy=false;btn.disabled=more.disabled=false;}
        };form.onsubmit=e=>{e.preventDefault();load(false);};more.onclick=()=>load(true);
    }
};

const RevisaoVisual = {
    mostrar(resultado,tipo) {
        const target=document.getElementById(tipo==='aluno'?'alunoItemDesc':'formItemDescricao');if(!target)return;
        let box=document.getElementById('revisaoVisual-'+tipo);if(!box){box=EvolucaoUI.node('section',undefined,'ev-visual');box.id='revisaoVisual-'+tipo;box.setAttribute('aria-label','Conferência da sugestão visual');target.closest('form').append(box);}
        box.replaceChildren();box.append(EvolucaoUI.node('p','Sugestões visuais: confira a foto antes de salvar.'));
        if(Array.isArray(resultado.cores)&&resultado.cores.length)box.append(EvolucaoUI.node('p','Cores sugeridas: '+resultado.cores.join(', ')+'. O fundo pode influenciar essa estimativa.'));
        if(resultado.ocr_confianca!=='alta')box.append(EvolucaoUI.node('p','Leitura do nome/RM com baixa confiança. Os campos abaixo precisam ser conferidos manualmente; nenhum dado da conta será alterado.'));
        for(const [name,key] of [['Nome escrito no objeto','ocr_nome_aluno'],['RM escrito no objeto','ocr_rm']]){
            const input=EvolucaoUI.field(box,name);input.maxLength=key==='ocr_rm'?20:100;input.value=resultado.ocr_confianca==='alta'?(resultado[key]||''):'';
            input.addEventListener('input',()=>{box.dataset.conferido='false';});
        }
        box.append(EvolucaoUI.node('p','Essas anotações servem à conferência da foto e não comprovam matrícula nem propriedade. Não são usadas para notificar uma pessoa por RM.'));
    }
};

document.addEventListener('DOMContentLoaded',()=>{
    const menu=document.querySelector('.menu-itens-lista');
    if(menu){for(const [label,action] of [['Retirada com código',()=>RetiradaSecretaria.abrir()],['Ocorrências dos objetos',()=>RetiradaSecretaria.historico()]]){const btn=EvolucaoUI.node('button',label,'item-menu');btn.type='button';btn.onclick=action;menu.append(btn);}}
    // A lista pessoal é reconstruída por outra rotina; delegação mantém os botões ativos.
    const list=document.getElementById('listaMinhasSolicitacoes');
    list?.addEventListener('click',event=>{const btn=event.target.closest('[data-codigo-retirada]');if(btn)RetiradasAluno.mostrar(btn.dataset.codigoRetirada);});
});
