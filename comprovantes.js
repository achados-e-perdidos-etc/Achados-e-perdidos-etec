/* A impressão usa uma cópia isolada; não envia dados para serviços externos. */
const ComprovantesEntrega = {
    ocupado:false, area:null, tituloAnterior:null,
    preparar(elemento){
        this.limpar();this.tituloAnterior=document.title;document.title='Comprovante de entrega';
        const area=document.createElement('section');area.id='areaImpressaoComprovante';area.className='comprovante-papel';
        const copia=elemento.cloneNode(true);
        for(const n of copia.querySelectorAll('button,[role=status],.ev-close'))n.remove();
        copia.removeAttribute('id');copia.removeAttribute('style');
        for(const n of copia.querySelectorAll('[id]'))n.removeAttribute('id');
        area.append(copia);document.body.append(area);this.area=area;return area;
    },
    async imprimir(elemento){
        if(this.ocupado)return;this.ocupado=true;
        try{
            const area=this.preparar(elemento);
            for(const img of area.querySelectorAll('img'))await img.decode();
            await document.fonts.ready;
            document.body.classList.add('imprimindo-comprovante');
            window.print();
        }catch(_){
            if(typeof mostrarToast==='function')mostrarToast('Não foi possível abrir a impressão. Confira se as imagens carregaram e tente novamente.');
        }finally{this.ocupado=false;this.limpar();}
    },
    limpar(){document.body.classList.remove('imprimindo-comprovante');this.area?.remove();this.area=null;if(this.tituloAnterior!==null){document.title=this.tituloAnterior;this.tituloAnterior=null;}},
    async abrirRegistro(id){
        const d=EvolucaoUI.dialog('Comprovante de entrega'),status=EvolucaoUI.node('p','Carregando comprovante privado…');status.setAttribute('role','status');d.append(status);
        let url=null;d.addEventListener('close',()=>{if(url)URL.revokeObjectURL(url);},{once:true});
        try{
            const token=EvolucaoUI.token(),data=await EvolucaoUI.request('/api/retiradas/comprovantes/'+Number(id));if(!d.isConnected)return;
            const registro=data.comprovante,folha=EvolucaoUI.node('article',undefined,'comprovante-papel');
            folha.append(EvolucaoUI.node('h2','ETEC · Achados e Perdidos'),EvolucaoUI.node('h3','Comprovante de entrega #'+registro.id));
            const campos=[['Objeto','#'+registro.item_id+' · '+registro.nome_item],['Recebido por',registro.retirado_por],['RM',registro.rm_retirante],['Turma / curso',registro.turma_curso||'Não informada'],['Entrega registrada em',registro.data_entrega],['Responsável',registro.funcionario_responsavel],['Forma de registro',registro.metodo==='CODIGO'?'Código e aceite presencial':'Registro pela secretaria']];
            const dl=document.createElement('dl');for(const [nome,valor] of campos){const box=document.createElement('div');box.append(EvolucaoUI.node('dt',nome),EvolucaoUI.node('dd',String(valor||'Não informado')));dl.append(box);}folha.append(dl);
            if(registro.cancelada_em)folha.append(EvolucaoUI.node('p','ENTREGA REVERTIDA em '+registro.cancelada_em+' por '+registro.cancelada_por+'. Este registro não representa uma entrega ativa.','comprovante-revertido'));
            d.append(folha);
            if(registro.tem_assinatura){
                const res=await fetch(API_URL+'/api/retiradas/comprovantes/'+Number(id)+'/assinatura',{headers:{Authorization:'Bearer '+token}});
                if(!res.ok||res.headers.get('Content-Type')?.split(';')[0]!=='image/jpeg')throw Error('O aceite não pôde ser carregado. Reabra o comprovante antes de imprimir.');
                const blob=await res.blob();if(!d.isConnected||token!==EvolucaoUI.token())return;
                url=URL.createObjectURL(blob);const img=document.createElement('img');img.src=url;img.alt='Assinatura ou aceite registrado no recebimento';folha.append(EvolucaoUI.node('h3','Aceite de recebimento'),img);await img.decode();
            }else folha.append(EvolucaoUI.node('p','Este registro não possui assinatura digitalizada.'));
            if(!d.isConnected||token!==EvolucaoUI.token())return;
            const print=EvolucaoUI.node('button','Imprimir comprovante','ev-action');print.type='button';print.onclick=()=>this.imprimir(folha);d.append(print);
            status.textContent='Escolha a impressora na janela de impressão, ou use Salvar como PDF.';
        }catch(error){if(d.isConnected)status.textContent=error.message||'Não foi possível carregar o comprovante. Reabra e tente novamente.';}
    }
};
