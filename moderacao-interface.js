/* Fluxos de correção e revisão preservam o cadastro e exigem confirmação da equipe. */
const ModeracaoUI = {
    estado:'PENDENTE',proximo:null,mais:false,ocupado:false,
    async duplicidade(payload) {
        const res=await fetch(API_URL+'/api/itens/duplicados',{method:'POST',headers:typeof getAuthHeaders==='function'?getAuthHeaders():{},body:JSON.stringify(payload)});
        const data=await res.json();if(!res.ok||!data.success)throw Error(data.message||'Não foi possível conferir duplicidade. Tente novamente.');
        const rows=data.duplicados||[],permitido=await this.confirmarDuplicados(rows);payload.confirmar_duplicado=rows.length>0&&permitido;return permitido;
    },
    confirmarDuplicados(rows) {
        if(!rows.length)return Promise.resolve(true);
        return new Promise(resolve=>{
            const d=EvolucaoUI.dialog('Objetos parecidos encontrados');let confirmado=false;
            d.append(EvolucaoUI.node('p','Compare estes registros antes de publicar. A semelhança é uma sugestão: objetos diferentes podem ter nomes iguais.','ev-note'));
            for(const row of rows){const box=EvolucaoUI.node('article',undefined,'mod-duplicado');box.append(EvolucaoUI.node('strong','#'+row.id+' · '+row.nome));box.append(EvolucaoUI.node('p',row.categoria+' · '+row.txt_data+' · '+row.status));d.append(box);}
            const yes=EvolucaoUI.node('button','Conferi: publicar mesmo assim');yes.type='button';yes.onclick=()=>{confirmado=true;d.close();};d.append(yes);
            const no=EvolucaoUI.node('button','Voltar e revisar');no.type='button';no.onclick=()=>d.close();d.append(no);
            d.addEventListener('close',()=>resolve(confirmado),{once:true});
        });
    },
    async carregar(mais=false) {
        if(this.ocupado)return;this.ocupado=true;
        const container=document.getElementById('gridItensPendentesContainer');
        if(!mais){this.proximo=null;itensPendentesSec=[];container.replaceChildren(EvolucaoUI.node('p','Buscando cadastros…'));}
        try{
            const data=await EvolucaoUI.request('/api/moderacao/cadastros?estado='+this.estado+(mais&&this.proximo?'&antes='+this.proximo:''));
            this.mais=data.tem_mais;this.proximo=data.proximo;
            itensPendentesSec=mais?[...itensPendentesSec,...data.cadastros]:data.cadastros;
            container.replaceChildren();
            if(!itensPendentesSec.length)container.append(EvolucaoUI.node('p',this.estado==='RECUSADO'?'Nenhum cadastro aguardando correção.':'Nenhum cadastro pendente de análise.'));
            for(const item of itensPendentesSec){
                const card=EvolucaoUI.node('article',undefined,'item-card');
                const info=EvolucaoUI.node('div',undefined,'item-info');info.append(EvolucaoUI.node('strong','#'+item.id+' · '+(item.nome||item.txt_descricao)));
                info.append(EvolucaoUI.node('p',item.categoria+' · '+item.txt_data+' · '+item.txt_local,'mod-resumo'));
                info.append(EvolucaoUI.node('p',item.txt_descricao,'mod-resumo'));
                if(item.motivo_recusa)info.append(EvolucaoUI.node('p','Motivo informado ao aluno: '+item.motivo_recusa,'mod-motivo'));
                const actions=EvolucaoUI.node('div',undefined,'mod-acao');
                for(const [text,fn] of [['Conferir fotos',()=>this.fotos(item)],['Histórico',()=>RetiradaSecretaria.historico(item.id)],['Aprovar',()=>this.aprovar(item)],['Pedir correção',()=>this.recusar(item)]]){const b=EvolucaoUI.node('button',text,'ev-action');b.type='button';b.onclick=fn;actions.append(b);}
                info.append(actions);card.append(info);container.append(card);
            }
            const more=document.getElementById('moderacaoMais');if(more)more.hidden=!this.mais;
        }catch(error){container.replaceChildren(EvolucaoUI.node('p',error.message,'ev-error'));}
        finally{this.ocupado=false;}
    },
    fotos(item){const d=EvolucaoUI.dialog('Fotos do cadastro #'+item.id);const fotos=Array.isArray(item.fotos)&&item.fotos.length?item.fotos:[item.foto].filter(Boolean);
        if(!fotos.length)d.append(EvolucaoUI.node('p','Este cadastro não tem fotos.'));
        for(const url of fotos){const src=urlImagemSegura(url);if(!src)continue;const img=document.createElement('img');img.src=src;img.loading='lazy';img.decoding='async';img.alt='Foto do objeto '+(item.nome||'');img.style.cssText='max-width:100%;border-radius:12px;margin:10px 0';d.append(img);}
    },
    async aprovar(item){
        if(this.ocupado)return;this.ocupado=true;
        try{
            const payload={id:item.id,nome:item.nome,categoria:item.categoria,data:item.txt_data};
            if(!await this.duplicidade(payload))return;
            const data=await EvolucaoUI.request('/api/itens/'+item.id+'/aprovar',{versao:item.versao,confirmar_duplicado:payload.confirmar_duplicado},'PUT');
            mostrarToast(data.message);this.ocupado=false;await this.carregar();carregarItensSecretaria();
        }catch(error){mostrarToast(error.message);}finally{this.ocupado=false;}
    },
    recusar(item){
        const d=EvolucaoUI.dialog('Devolver cadastro para correção'),form=document.createElement('form');
        d.append(EvolucaoUI.node('p','O aluno verá o motivo e poderá corrigir este mesmo cadastro. Fotos e histórico serão preservados.'));
        const label=EvolucaoUI.node('label','Explique o que precisa ser corrigido','ev-field'),reason=document.createElement('textarea');reason.required=true;reason.minLength=5;reason.maxLength=1000;reason.rows=4;reason.style.cssText='display:block;width:100%;padding:10px;background:#0c1523;color:white;border:1px solid #8493aa;border-radius:9px';reason.value=item.motivo_recusa||'';label.append(reason);form.append(label);
        const submit=EvolucaoUI.node('button','Enviar motivo ao aluno');submit.type='submit';const status=EvolucaoUI.node('p','');status.setAttribute('role','status');form.append(submit,status);d.append(form);
        form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;try{const data=await EvolucaoUI.request('/api/itens/'+item.id+'/recusar',{versao:item.versao,motivo:reason.value.trim()});mostrarToast(data.message);d.close();await this.carregar();}catch(error){status.textContent=error.message;}finally{submit.disabled=false;}};
    },
    iniciar(){
        const grid=document.getElementById('gridItensPendentesContainer');if(!grid)return;
        const label=EvolucaoUI.node('label','Exibir cadastros: ','ev-field'),select=document.createElement('select');select.id='moderacaoEstado';select.className='ev-action';
        for(const [value,text] of [['PENDENTE','Aguardando análise'],['RECUSADO','Devolvidos para correção']]){const opt=EvolucaoUI.node('option',text);opt.value=value;select.append(opt);}
        select.onchange=()=>{if(this.ocupado){select.value=this.estado;return;}this.estado=select.value;this.carregar();};label.append(select);grid.before(label);
        const more=EvolucaoUI.node('button','Ver cadastros anteriores','ev-action');more.id='moderacaoMais';more.type='button';more.hidden=true;more.onclick=()=>this.carregar(true);grid.after(more);
    }
};

const CorrecaoCadastro = {
    atual:null,abrindo:false,
    cancelar(){this.atual=null;document.getElementById('motivoCorrecaoCadastro')?.remove();const b=document.getElementById('btnSalvarAlunoItem');if(b)b.textContent='Enviar para análise da secretaria';},
    async abrir(id){
        try{
            const data=await EvolucaoUI.request('/api/meus-cadastros/'+Number(id));const item=data.item;
            if(!item.pode_corrigir)throw Error('O cadastro mudou. Atualize Minha atividade.');
            abrirModalCadastrarAluno();this.atual={id:item.id,versao:item.versao,data:item.txt_data};
            for(const [field,value] of Object.entries({alunoItemNome:item.nome,alunoItemDesc:item.txt_descricao,alunoItemCat:item.categoria,alunoItemLocal:item.txt_local,alunoItemData:CatalogoPortal.dataISO(item.txt_data)}))document.getElementById(field).value=value||'';
            fotosAlunoSelecionadas=(item.fotos||[]).slice();renderizarGridPreviewAluno();
            const reason=EvolucaoUI.node('p','Orientação da secretaria: '+(item.motivo_recusa||'Confira o cadastro.'),'mod-motivo');reason.id='motivoCorrecaoCadastro';document.getElementById('alunoItemNome').closest('form').prepend(reason);
            document.getElementById('btnSalvarAlunoItem').textContent='Reenviar cadastro para análise';
        }catch(error){mostrarToast(error.message,'error');}
    }
};

document.addEventListener('DOMContentLoaded',()=>ModeracaoUI.iniciar());
