/* Fila com consentimento, expiração e identidade. Nunca persiste senha ou JWT. */
const FilaOffline = {
    db: null, busy: false, versao: 0, uploader: null, ttl: 24*60*60*1000,
    conta() {try{return SessaoPortal.dados()?.email||null;}catch(_){return null;}},
    async abrir() {
        if(this.db)return this.db;
        return new Promise((resolve,reject)=>{
            const r=indexedDB.open('etec-envios-offline-v1',1);
            r.onupgradeneeded=()=>{const s=r.result.createObjectStore('envios',{keyPath:'id'});s.createIndex('email','email');};
            r.onsuccess=()=>{this.db=r.result;resolve(this.db);};r.onerror=()=>reject(Error('O navegador não permitiu guardar o cadastro.'));
        });
    },
    async transacao(mode,action) {
        const db=await this.abrir();
        return new Promise((resolve,reject)=>{
            const tx=db.transaction('envios',mode),r=action(tx.objectStore('envios'));let result;
            if(r)r.onsuccess=()=>{result=r.result;};
            tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(Error('Não foi possível atualizar os envios salvos.'));
        });
    },
    async listar() {
        const rows=await this.transacao('readonly',s=>s.getAll())||[],expired=rows.filter(row=>Date.now()-row.criado>=this.ttl);
        if(expired.length)await this.transacao('readwrite',s=>{expired.forEach(row=>s.delete(row.id));});
        return rows.filter(row=>Date.now()-row.criado<this.ttl);
    },
    avisar(text) {const el=document.getElementById('filaOfflineStatus');if(el)el.textContent=text;},
    async guardar(tipo,payload) {
        const email=this.conta(),version=this.versao;if(!email)throw Error('Entre em sua conta antes de guardar o cadastro.');
        const texto=JSON.stringify(payload);
        if(texto.length>6*1024*1024)throw Error('Este cadastro tem fotos demais para guardar offline. Remova uma foto ou aguarde a conexão.');
        const db=await this.abrir();
        // Limites verificados e gravação feitos na mesma transação, inclusive entre abas.
        await new Promise((resolve,reject)=>{
            const tx=db.transaction('envios','readwrite'),store=tx.objectStore('envios'),all=store.getAll();let message;
            all.onsuccess=()=>{
                if(email!==this.conta()||version!==this.versao){message='A conta mudou. Abra o formulário novamente.';tx.abort();return;}
                const rows=all.result.filter(row=>Date.now()-row.criado<this.ttl);
                all.result.filter(row=>Date.now()-row.criado>=this.ttl).forEach(row=>store.delete(row.id));
                if(rows.filter(row=>row.email===email).length>=10||rows.reduce((n,row)=>n+JSON.stringify(row).length,0)+texto.length>16*1024*1024){message='A fila offline está cheia. Envie ou descarte cadastros antigos.';tx.abort();return;}
                store.put({id:crypto.randomUUID(),email,tipo,payload,criado:Date.now(),erro:null});
            };
            tx.oncomplete=resolve;tx.onerror=tx.onabort=()=>reject(Error(message||'Não foi possível guardar neste dispositivo. O formulário foi mantido.'));
        });
        this.avisar('Cadastro guardado neste dispositivo por até 24 horas. Será enviado quando a conexão voltar e sua conta estiver ativa.');
        if(navigator.onLine){if(this.busy)this.novosDuranteSync=true;else this.sincronizar();}
    },
    async sair() {
        const email=this.conta();this.versao++;this.uploader?.limpar();this.uploader=null;
        document.querySelectorAll('.ev-queue-dialog').forEach(d=>d.close());
        if(email)try{await this.transacao('readwrite',s=>{const r=s.index('email').openCursor(IDBKeyRange.only(email));r.onsuccess=()=>{const c=r.result;if(c){c.delete();c.continue();}};});}catch(_){}
        this.avisar('Os envios locais desta conta foram removidos ao sair.');
    },
    async sincronizar() {
        if(this.busy)return this.terminou;
        if(!navigator.onLine||!this.conta())return;
        this.busy=true;this.terminou=new Promise(resolve=>{this.finalizar=resolve;});
        const email=this.conta(),token=SessaoPortal.token(),version=this.versao;
        try {
            const auth=await fetch(API_URL+'/api/auth/verificar',{headers:{Authorization:'Bearer '+token}});
            const identity=await auth.json();
            if(!auth.ok||!identity.success||identity.user.email!==email)throw Error('Entre novamente para sincronizar a fila offline.');
            const rows=await this.listar();
            for(const row of rows){
                if(row.email!==email)continue;
                if(Date.now()-row.criado>=this.ttl){await this.transacao('readwrite',s=>s.delete(row.id));continue;}
                if(version!==this.versao||token!==SessaoPortal.token()||email!==this.conta())break;
                if(row.bloqueado)continue;
                this.avisar('Sincronizando '+(row.tipo==='mural'?'relato de perda':'objeto encontrado')+'…');
                try {
                    const payload=row.envio||{...row.payload};
                    if(!row.envio&&row.tipo==='encontrado'&&payload.fotos?.length){
                        const holder=document.createElement('div');holder.id='filaUpload-'+row.id;
                        document.getElementById('filaOfflineProgresso').replaceChildren(holder);
                        this.uploader=new UploadFotos(holder.id,()=>token);
                        payload.fotos=await this.uploader.enviarTodas(payload.fotos);
                    }
                    if(version!==this.versao||token!==SessaoPortal.token())break;
                    // Guarda as URLs confirmadas antes de publicar: toda repetição usa o mesmo corpo.
                    if(!row.envio){row.envio=payload;await this.transacao('readwrite',s=>{if(version===this.versao&&email===this.conta()&&token===SessaoPortal.token())s.put(row);});}
                    if(version!==this.versao||token!==SessaoPortal.token())break;
                    const res=await fetch(API_URL+(row.tipo==='mural'?'/api/mural':'/api/itens/cadastrar-aluno'),{
                        method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json','Idempotency-Key':row.id},body:JSON.stringify(row.envio)});
                    const data=await res.json();if(!res.ok||!data.success){const error=Error(data.message||'O servidor não confirmou o cadastro.');error.status=res.status;throw error;}
                    if(version===this.versao)await this.transacao('readwrite',s=>s.delete(row.id));
                    this.avisar('Cadastro sincronizado e removido deste dispositivo.');
                }catch(error){
                    if(version!==this.versao)break;
                    row.erro=error.message;row.bloqueado=[400,403,409,413,422].includes(error.status);
                    await this.transacao('readwrite',s=>{if(version===this.versao&&email===this.conta()&&token===SessaoPortal.token())s.put(row);});
                    this.avisar('Um cadastro não pôde ser enviado. Os demais continuam. Abra a fila para conferir.');
                    if(error.status===401)break;
                }finally{this.uploader=null;}
            }
        }catch(error){this.avisar(error.message||'A conexão falhou. Os cadastros continuam guardados.');}
        finally{this.busy=false;this.finalizar();if(this.novosDuranteSync){this.novosDuranteSync=false;queueMicrotask(()=>this.sincronizar());}}
    },
    async mostrar() {
        const d=EvolucaoUI.dialog('Envios guardados neste dispositivo');d.classList.add('ev-queue-dialog');
        d.append(EvolucaoUI.node('p','Somente cadastros de objetos e relatos de perda entram na fila. Expiram em 24 horas e são apagados ao sair da conta. A sincronização automática funciona com o site aberto e sessão válida.','ev-note'));
        const status=EvolucaoUI.node('p','Carregando…');status.setAttribute('role','status');d.append(status);
        try {
            const email=this.conta(),rows=(await this.listar()).filter(r=>r.email===email);if(!d.isConnected||email!==this.conta())return;
            status.textContent=rows.length?'Confira os cadastros abaixo.':'Nenhum envio pendente nesta conta.';
            for(const row of rows){const card=EvolucaoUI.node('article',undefined,'ev-job');
                card.append(EvolucaoUI.node('strong',row.payload.nome||'Relato: '+row.payload.categoria));
                card.append(EvolucaoUI.node('p',row.erro||'Aguardando conexão.'));
                const expires=Date.now()-row.criado>=this.ttl;card.append(EvolucaoUI.node('p',expires?'Expirado: descarte e cadastre novamente.':'Expira em '+new Date(row.criado+this.ttl).toLocaleString('pt-BR')));
                const remove=EvolucaoUI.node('button','Descartar');remove.onclick=async()=>{if(this.busy){status.textContent='Aguarde a sincronização terminar.';return;}if(!confirm('Descartar este cadastro salvo?'))return;await this.transacao('readwrite',s=>s.delete(row.id));card.remove();};card.append(remove);d.append(card);
            }
            const sync=EvolucaoUI.node('button','Tentar sincronizar');sync.onclick=async()=>{sync.disabled=true;await this.sincronizar();sync.disabled=false;status.textContent='Tentativa concluída. Feche e abra a fila para atualizar a lista.';};d.append(sync);
        }catch(error){status.textContent=error.message;}
    },
    iniciar() {
        if(!document.getElementById('alunoItemNome'))return;
        if('serviceWorker' in navigator && window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(()=>{});
        const area=EvolucaoUI.node('section',undefined,'ev-offline-box');area.id='filaOfflineArea';
        const state=EvolucaoUI.node('p','Envios offline: a fila fica neste dispositivo e é apagada ao sair da conta.');state.id='filaOfflineStatus';state.setAttribute('role','status');
        const view=EvolucaoUI.node('button','Ver fila offline','ev-action');view.type='button';view.onclick=()=>this.mostrar();
        const progress=document.createElement('div');progress.id='filaOfflineProgresso';area.append(state,view,progress);document.getElementById('meusItensScreen').prepend(area);
        for(const [tipo,id] of [['encontrado','alunoItemNome'],['mural','muralDescricao']]){
            const input=document.getElementById(id),form=input.closest('form'),label=EvolucaoUI.node('label',undefined,'ev-offline-box'),check=document.createElement('input');check.type='checkbox';check.id='offlineConsent-'+tipo;
            label.append(check,document.createTextNode('Se estiver sem internet, guardar este cadastro e suas fotos neste dispositivo por até 24 horas e enviar automaticamente ao reconectar. Evite em aparelhos compartilhados.'));form.append(label);
            form.addEventListener('submit',async event=>{
                if(navigator.onLine)return;
                event.preventDefault();event.stopImmediatePropagation();
                if(tipo==='encontrado'&&typeof CorrecaoCadastro!=='undefined'&&CorrecaoCadastro.atual){mostrarToast('Conecte-se para reenviar esta correção com a versão atual do cadastro.','info');return;}
                if(!check.checked){mostrarToast('Marque a opção de guardar offline ou aguarde a conexão.','info');return;}
                if(typeof preparandoFotosAluno!=='undefined'&&preparandoFotosAluno){mostrarToast('Aguarde a preparação das fotos.','info');return;}
                const payload=tipo==='mural'?{categoria:document.getElementById('muralCategoria').value,descricao:input.value.trim()}:{nome:input.value.trim(),descricao:document.getElementById('alunoItemDesc').value.trim(),categoria:document.getElementById('alunoItemCat').value,local:document.getElementById('alunoItemLocal').value.trim(),data:document.getElementById('alunoItemData')?.value||new Date().toLocaleDateString('pt-BR'),fotos:[...fotosAlunoSelecionadas]};
                try{await this.guardar(tipo,payload);Rascunhos.limpar(tipo);form.reset();if(tipo==='encontrado'){fotosAlunoSelecionadas=[];UploadAluno.limpar();renderizarGridPreviewAluno();document.getElementById('modalCadastrarAluno').classList.add('hidden');}mostrarToast('Guardado no dispositivo. Ainda não foi enviado à escola.','info');}
                catch(error){mostrarToast(error.message,'error');}
            },true);
        }
        window.addEventListener('online',()=>this.sincronizar());
        window.addEventListener('storage',()=>{this.versao++;this.uploader?.limpar();document.querySelectorAll('.ev-queue-dialog').forEach(d=>d.close());});
        // Só inicia rede automaticamente se houver envios; evita consultas sem necessidade.
        this.listar().then(rows=>{if(rows.some(r=>r.email===this.conta()))this.sincronizar();}).catch(()=>{});
    }
};
document.addEventListener('DOMContentLoaded',()=>FilaOffline.iniciar());
