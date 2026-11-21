/* Fotos privadas: somente blobs autenticados; nunca URLs de foto no armazenamento local. */
const PerfilUI={
    proprio:null,url:null,epoca:0,
    token(){return EvolucaoUI.token();},
    limpar(){this.epoca++;this.proprio=null;if(this.url)URL.revokeObjectURL(this.url);this.url=null;document.querySelectorAll('.perfil-privado').forEach(d=>d.close());document.querySelectorAll('.foto-propria').forEach(i=>{i.hidden=true;i.removeAttribute('src');});},
    async carregar(){
        const e=++this.epoca;try{
            const data=await EvolucaoUI.request('/api/perfil');if(e!==this.epoca||!data.perfil)return;
            this.proprio=data.perfil;let url=null;
            if(data.perfil.foto_id){const r=await fetch(API_URL+'/api/perfil/foto/'+encodeURIComponent(data.perfil.foto_id),{headers:{Authorization:'Bearer '+this.token()}});if(!r.ok)throw Error('Foto indisponível.');url=URL.createObjectURL(await r.blob());}
            if(e!==this.epoca){if(url)URL.revokeObjectURL(url);return;}if(this.url)URL.revokeObjectURL(this.url);this.url=url;
            document.querySelectorAll('.foto-propria').forEach(img=>{if(url){img.src=url;img.hidden=false;}else{img.hidden=true;img.removeAttribute('src');}});
        }catch(_){/* O perfil mantém o ícone padrão se a consulta estiver indisponível. */}
    },
    async abrir(){
        document.getElementById('perfilMenu')?.classList.add('hidden');
        const d=EvolucaoUI.dialog('Minha foto de perfil');d.classList.add('perfil-privado');let previewUrl=null,ocupado=false;
        d.append(EvolucaoUI.node('p','Sua foto é opcional e só pode ser vista por você e pela equipe autorizada. Você pode removê-la quando quiser.'));
        const guia=EvolucaoUI.node('ul',undefined,'perfil-dicas');for(const t of ['Use uma foto só sua, de frente, mostrando a cabeça e os ombros.','Deixe o rosto inteiro e os dois olhos visíveis, com boa iluminação.','Evite máscara, óculos escuros, filtros, montagens e objetos cobrindo o rosto.','Envie JPEG, PNG ou WEBP, com até 2 MB e pelo menos 200 × 200 pixels.'])guia.append(EvolucaoUI.node('li',t));d.append(guia);
        const img=document.createElement('img');img.className='perfil-previa foto-propria';img.alt='Sua foto de perfil';img.hidden=!this.url;if(this.url)img.src=this.url;d.append(img);
        const campo=EvolucaoUI.field(d,'Escolher uma foto','file');campo.accept='image/jpeg,image/png,image/webp';
        const status=EvolucaoUI.node('p','A pré-verificação procura rosto e olhos visíveis. Ela não comprova identidade nem autenticidade.','ev-status');status.setAttribute('role','status');d.append(status);
        const salvar=EvolucaoUI.node('button','Salvar foto','ev-action'),remover=EvolucaoUI.node('button','Remover minha foto','ev-action');salvar.type=remover.type='button';salvar.disabled=true;d.append(salvar,remover);
        campo.onchange=()=>{const f=campo.files?.[0];if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;salvar.disabled=true;
            if(!f)return;if(!['image/jpeg','image/png','image/webp'].includes(f.type)||f.size>2*1024*1024){status.textContent='Selecione JPEG, PNG ou WEBP de até 2 MB.';campo.value='';return;}
            previewUrl=URL.createObjectURL(f);img.src=previewUrl;img.hidden=false;salvar.disabled=false;status.textContent='Prévia: a foto ainda não foi salva. Confira as orientações e toque em Salvar foto.';
        };
        const enviar=async(apagar=false)=>{if(ocupado)return;ocupado=true;salvar.disabled=remover.disabled=campo.disabled=true;status.textContent=apagar?'Removendo foto…':'Conferindo o enquadramento e preparando uma foto pequena…';
            try{let payload={};if(!apagar){const f=campo.files?.[0];if(!f)throw Error('Selecione uma foto.');const foto=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('Não foi possível ler a foto.'));r.readAsDataURL(f);});payload={foto};}
                const data=await EvolucaoUI.request('/api/perfil/foto',payload,apagar?'DELETE':'POST');status.textContent=data.message;campo.value='';if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null;}await this.carregar();if(!this.url){img.hidden=true;img.removeAttribute('src');}
            }catch(e){status.textContent=e.message;}finally{ocupado=false;campo.disabled=remover.disabled=false;salvar.disabled=!campo.files?.length;}
        };salvar.onclick=()=>enviar();remover.onclick=()=>enviar(true);
        d.addEventListener('close',()=>{if(previewUrl)URL.revokeObjectURL(previewUrl);},{once:true});
    },
    async verAluno(alvo){
        const d=EvolucaoUI.dialog('Perfil para conferência');d.classList.add('perfil-privado');d.append(EvolucaoUI.node('p','Foto informada pelo usuário: confira também o documento, o RM e os detalhes da retirada. A foto não comprova identidade.'));
        const status=EvolucaoUI.node('p','Consultando perfil…');d.append(status);let url=null;
        d.addEventListener('close',()=>{if(url)URL.revokeObjectURL(url);},{once:true});
        try{const data=await EvolucaoUI.request('/api/secretaria/perfil',typeof alvo==='string'?{email:alvo}:alvo,'POST');if(!d.isConnected)return;const perfil=data.perfil;
            status.textContent=perfil.nome+' · RM: '+perfil.rm;d.append(EvolucaoUI.node('p',perfil.email));
            if(!perfil.foto_id){d.append(EvolucaoUI.node('p','Esta conta ainda não cadastrou foto.'));return;}
            const token=this.token(),res=await fetch(API_URL+'/api/perfil/foto/'+encodeURIComponent(perfil.foto_id),{headers:{Authorization:'Bearer '+token}});if(!res.ok)throw Error('Não foi possível carregar a foto.');const blob=await res.blob();if(!d.isConnected||token!==this.token())return;
            url=URL.createObjectURL(blob);const img=document.createElement('img');img.src=url;img.alt='Foto de perfil informada por '+perfil.nome;img.className='perfil-previa';d.append(img);
        }catch(e){if(d.isConnected)status.textContent=e.message;}
    },
    iniciar(){
        window.addEventListener('storage',e=>{if(['aluno_token','secretaria_token'].includes(e.key)||e.key===null)this.limpar();});
        const menu=document.getElementById('perfilMenu');if(menu){
            const btn=menu.previousElementSibling;btn.classList.add('perfil-botao-foto');btn.setAttribute('aria-label','Abrir meu perfil');const img=document.createElement('img');img.hidden=true;img.alt='Minha foto';img.className='foto-propria perfil-avatar';btn.append(img);
            const foto=EvolucaoUI.node('button','Minha foto de perfil','ev-action');foto.type='button';foto.onclick=()=>this.abrir();menu.append(foto);
            if(typeof alunoSessao!=='undefined'&&alunoSessao)this.carregar();
        }
        if(document.getElementById('inputBusca')){
            const anterior=abrirDetalhesItem;abrirDetalhesItem=id=>{anterior(id);const item=itensSec.find(i=>Number(i.id)===Number(id));const box=document.querySelector('#modalDetalhesItem .modal-box');box.querySelector('.perfil-solicitante')?.remove();if(item?.status==='SOLICITADO'){const b=EvolucaoUI.node('button','Ver perfil do solicitante','ev-action perfil-solicitante');b.type='button';b.onclick=()=>this.verAluno({item_id:Number(item.id)});box.append(b);}};
            const chat=selecionarConversaAluno;selecionarConversaAluno=async(...args)=>{await chat(...args);document.querySelector('.perfil-contato')?.remove();if(!chatEmailAtivo)return;const email=chatEmailAtivo,b=EvolucaoUI.node('button','Ver perfil e foto','ev-action perfil-contato');b.type='button';b.onclick=()=>this.verAluno(email);document.querySelector('.chat-conversa-header').append(b);};
        }
    }
};

const TermosUI={
    dados:null,lida:null,
    reiniciar(){this.lida=null;const check=document.getElementById('aceiteTermos');if(check){check.checked=false;check.disabled=true;document.getElementById('statusTermos').textContent='Abra os termos e percorra o texto até o fim para habilitar o aceite.';}},
    async carregar(){
        try{const r=await fetch(API_URL+'/api/termos'),d=await r.json();if(!r.ok||!d.success||typeof d.versao!=='string'||!Array.isArray(d.secoes)||!d.secoes.length)throw Error();
            if(this.dados?.versao!==d.versao){this.lida=null;const check=document.getElementById('aceiteTermos');check.disabled=true;check.checked=false;}this.dados=d;
            document.getElementById('statusTermos').textContent=this.lida===d.versao?'Texto percorrido. Marque a caixa se concordar com os termos.':'Abra os termos e percorra o texto até o fim para habilitar o aceite.';
        }catch(_){this.dados=null;this.lida=null;const check=document.getElementById('aceiteTermos');check.disabled=true;check.checked=false;document.getElementById('statusTermos').textContent='Não foi possível carregar os termos. Toque em Ler os termos para tentar novamente.';}
    },
    async abrir(){
        await this.carregar();if(!this.dados)return;const dados=this.dados,d=EvolucaoUI.dialog('Termos de Uso e informações sobre dados');
        d.append(EvolucaoUI.node('p','Versão '+dados.versao+' · percorra o texto até o fim.'));
        const texto=EvolucaoUI.node('div',undefined,'termos-leitura');texto.tabIndex=0;texto.setAttribute('role','region');texto.setAttribute('aria-label','Texto completo dos termos; use as setas ou role até o final');
        for(const s of dados.secoes){texto.append(EvolucaoUI.node('h3',s.titulo),EvolucaoUI.node('p',s.texto));}d.append(texto);
        const aviso=EvolucaoUI.node('p','Role até o fim para liberar a caixa de aceite.','ev-status');aviso.setAttribute('role','status');d.append(aviso);
        const concluir=EvolucaoUI.node('button','Voltar ao cadastro','ev-action');concluir.type='button';concluir.onclick=()=>d.close();d.append(concluir);
        const fim=()=>{if(!texto.clientHeight||texto.scrollTop+texto.clientHeight<texto.scrollHeight-3||this.dados?.versao!==dados.versao)return;const primeiro=this.lida!==dados.versao;this.lida=dados.versao;const check=document.getElementById('aceiteTermos');check.disabled=false;if(primeiro)check.checked=false;document.getElementById('statusTermos').textContent='Texto percorrido. Marque a caixa se concordar com os termos.';aviso.textContent='Você chegou ao final. Volte ao cadastro e marque o aceite se concordar.';};
        texto.addEventListener('scroll',fim,{passive:true});requestAnimationFrame(fim);
    },
    valido(){return !!this.lida&&this.lida===this.dados?.versao&&document.getElementById('aceiteTermos')?.checked===true;},
    iniciar(){const b=document.getElementById('lerTermos');if(!b)return;b.onclick=()=>this.abrir();this.carregar();}
};
document.addEventListener('DOMContentLoaded',()=>{PerfilUI.iniciar();TermosUI.iniciar();});
