/* Partes de 64 KB confirmadas pelo servidor, independentes para cada foto. */
class UploadFotos {
    constructor(id, token) { this.id=id;this.token=token;this.arquivos=new Map();this.versao=0;this.controller=new AbortController(); }
    limpar() { this.versao++;this.controller.abort();this.controller=new AbortController();this.arquivos.clear();document.getElementById(this.id)?.replaceChildren(); }
    mostrar(fotos) {
        let box=document.getElementById(this.id);
        if (!box) return;
        for(const [foto,item] of this.arquivos) {
            if(!fotos.includes(foto)&&!item.ocupado){if(item.id)this.requisicao('/api/uploads/'+item.id,{method:'DELETE'},this.token()).catch(()=>{});this.arquivos.delete(foto);}
        }
        box.replaceChildren();
        for(const item of this.arquivos.values())item.uis=[];
        fotos.forEach((foto,indice)=>{
            if (/^https?:/.test(foto)) return;
            let item=this.arquivos.get(foto);
            if (!item) {item={foto,id:null,offset:0,url:null,ocupado:false,erro:false};this.arquivos.set(foto,item);}
            const card=document.createElement('div');card.className='upload-arquivo';
            const titulo=document.createElement('strong');titulo.textContent=`Foto ${indice+1}`;
            const barra=document.createElement('progress');barra.max=100;barra.value=item.url?100:0;barra.setAttribute('aria-label',`Envio da foto ${indice+1}`);
            const estado=document.createElement('span');estado.setAttribute('role','status');
            const botao=document.createElement('button');botao.type='button';botao.textContent='Tentar novamente';botao.addEventListener('click',()=>this.enviar(item).catch(()=>{}));
            (item.uis ||= []).push({barra,estado,botao});card.append(titulo,barra,estado,botao);box.append(card);this.atualizar(item);
        });
    }
    atualizar(item) {
        for(const ui of item.uis || []) {
        ui.barra.value=item.url?100:item.total?Math.floor(item.offset/item.total*100):0;
        ui.estado.textContent=item.url?'Enviada ✓':item.erro?'Envio interrompido. As partes recebidas foram preservadas.':item.ocupado?(item.offset===item.total?'Concluindo armazenamento…':`Enviando: ${ui.barra.value}%`):'Pronta para enviar';
        ui.botao.hidden=!item.erro;ui.botao.disabled=item.ocupado;
        }
    }
    async requisicao(path,opcoes,token) {
        const parent=this.controller.signal,controller=new AbortController();
        const abortar=()=>controller.abort();
        if(parent.aborted)abortar();else parent.addEventListener('abort',abortar,{once:true});
        const timer=setTimeout(abortar,path.endsWith('/finalizar')?60000:30000);
        try {
            const res=await fetch(API_URL+path,{...opcoes,signal:controller.signal,headers:{Authorization:`Bearer ${token}`,...opcoes?.headers}});
            const data=await res.json();
            if (!res.ok) {const error=Error(data.message||'Envio interrompido.');error.status=res.status;error.offset=data.recebidos;throw error;}
            return data;
        } finally {clearTimeout(timer);parent.removeEventListener('abort',abortar);}

    }
    async enviar(item) {
        if(item.url)return item.url;
        if(item.ocupado)return item.promessa;
        item.ocupado=true;item.erro=false;const versao=this.versao,token=this.token();this.atualizar(item);
        item.promessa=(async()=>{
            try {
                if(!item.blob) {
                    const partes=item.foto.split(',');const bytes=Uint8Array.from(atob(partes[1]),c=>c.charCodeAt(0));
                    item.blob=new Blob([bytes],{type:'image/jpeg'});item.total=bytes.length;
                    item.hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
                }
                if(!item.id) {
                    const data=await this.requisicao('/api/uploads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tamanho:item.total,sha256:item.hash,retomar:true})},token);item.id=data.id;
                }
                const status=await this.requisicao('/api/uploads/'+item.id,{},token);item.offset=status.recebidos;
                if(status.url){item.url=status.url;return item.url;}
                while(item.offset<item.total) {
                    const parte=item.blob.slice(item.offset,item.offset+65536);
                    try {
                        const data=await this.requisicao('/api/uploads/'+item.id+'/parte',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Upload-Offset':String(item.offset)},body:parte},token);
                        item.offset=data.recebidos;
                    } catch(error) {
                        if(error.status===409&&Number.isInteger(error.offset)&&error.offset>item.offset){item.offset=error.offset;}
                        else throw error;
                    }
                    if(versao!==this.versao)throw Error('Sessão encerrada.');this.atualizar(item);
                }
                const concluido=await this.requisicao('/api/uploads/'+item.id+'/finalizar',{method:'POST'},token);
                item.url=concluido.url;return item.url;
            } catch(error) {if(versao===this.versao)item.erro=true;throw error;}
            finally{item.ocupado=false;if(versao===this.versao)this.atualizar(item);}
        })();return item.promessa;
    }
    async enviarTodas(fotos) {
        this.mostrar(fotos);
        const resultados=await Promise.allSettled(fotos.map(f=>/^https?:/.test(f)?Promise.resolve(f):this.enviar(this.arquivos.get(f))));
        if(resultados.some(r=>r.status==='rejected'))throw Error('Uma ou mais fotos não foram concluídas. Use Tentar novamente na foto que falhou.');
        return resultados.map(r=>r.value);
    }
}
