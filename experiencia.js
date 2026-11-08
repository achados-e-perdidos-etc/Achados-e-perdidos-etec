/* Orientação contextual e navegação; usa os fluxos e a sessão já existentes. */
const ExperienciaUI = {
    scrollCatalogo:0, focoCatalogo:null,
    aba(aba){
        for(const b of document.querySelectorAll('[data-ux-aba]')){
            if(b.dataset.uxAba===aba)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
        }
        const hero=document.getElementById('portalBoasVindas');if(hero)hero.hidden=aba!=='catalogo';
        const ajuda=document.querySelector('.ux-como-funciona');if(ajuda)ajuda.hidden=aba!=='catalogo';
    },
    detalhe(item,status){
        this.scrollCatalogo=window.scrollY;this.focoCatalogo=document.activeElement;
        this.aba('catalogo');document.getElementById('portalBoasVindas').hidden=true;document.querySelector('.ux-como-funciona').hidden=true;
        let n=document.getElementById('detailProximoPasso');
        if(!n){n=document.createElement('div');n.id='detailProximoPasso';n.className='ux-next-step';document.getElementById('btnSolicitar').before(n);}
        const title=document.createElement('strong'),text=document.createElement('p');
        const conteudo={
            'DISPONÍVEL':['A retirada é confirmada presencialmente','Se reconhecer este objeto, faça a solicitação. Leve seu RM, documento e o código de retirada à secretaria para a conferência.'],
            'SOLICITADO':['Este objeto já tem uma solicitação','Se o pedido é seu, consulte Minha atividade para obter o código de retirada. Se precisar de ajuda, converse com a secretaria.'],
            'ENTREGUE':['Devolução registrada','A secretaria registrou a entrega deste objeto. Se tiver alguma dúvida, entre em contato pelo chat.'],
            'PARA DOAÇÃO':['Objeto separado para doação','Consulte a secretaria para saber a situação atual deste objeto.'],
            'DOAÇÃO FEITA':['Doação registrada','Este objeto já saiu do estoque. Consulte a secretaria se precisar de mais informações.']
        }[status]||['Precisa de ajuda?','Converse com a secretaria para conferir a situação deste objeto.'];
        title.textContent=conteudo[0];text.textContent=conteudo[1];n.replaceChildren(title,text);
        const heading=document.getElementById('detailTitle');heading.tabIndex=-1;heading.focus({preventScroll:true});
        document.getElementById('detailScreen').scrollIntoView({block:'start',behavior:'instant'});
    },
    voltar(){window.scrollTo({top:this.scrollCatalogo,behavior:'instant'});if(this.focoCatalogo?.isConnected)this.focoCatalogo.focus({preventScroll:true});},
    auth(tela){
        const titulos={login:['Vamos encontrar o que é seu.','Entre com sua conta institucional de aluno ou professor.'],cadastro:['Faça parte dos reencontros.','Confirme seu e-mail institucional para criar sua conta.'],recuperar:['Recupere seu acesso.','Enviaremos um código ao seu e-mail institucional.']};
        const copy=titulos[tela]||titulos.login;document.getElementById('authTitulo').textContent=copy[0];document.getElementById('authDescricao').textContent=copy[1];this.limparFeedback();
    },
    limparFeedback(){const n=document.getElementById('authFeedback');if(n){n.hidden=true;n.textContent='';}},
    feedback(mensagem,tipo){
        const n=document.getElementById('authFeedback'),login=document.getElementById('loginAlunoScreen');
        if(!n||login?.classList.contains('hidden'))return;
        n.textContent=String(mensagem);n.hidden=false;n.setAttribute('role',tipo==='error'?'alert':'status');
    },
    senha(id){
        const input=document.getElementById(id);if(!input)return;
        let wrap=input.parentElement;
        if(!wrap.classList.contains('relative')){wrap=document.createElement('div');input.before(wrap);wrap.append(input);}
        wrap.classList.add('ux-password-wrap');
        const btn=document.createElement('button');btn.type='button';btn.className='ux-password-toggle';btn.textContent='Mostrar';btn.setAttribute('aria-controls',id);btn.setAttribute('aria-pressed','false');btn.setAttribute('aria-label','Mostrar senha');
        btn.onclick=()=>{const visivel=input.type==='password';input.type=visivel?'text':'password';btn.textContent=visivel?'Ocultar':'Mostrar';btn.setAttribute('aria-pressed',String(visivel));btn.setAttribute('aria-label',visivel?'Ocultar senha':'Mostrar senha');};wrap.append(btn);
        document.getElementById('loginAlunoScreen')?.addEventListener('submit',()=>{input.type='password';btn.textContent='Mostrar';btn.setAttribute('aria-pressed','false');btn.setAttribute('aria-label','Mostrar senha');});
    },
    formularios(){
        document.addEventListener('invalid',evento=>{
            const campo=evento.target;if(!campo.id||!campo.validity)return;
            const id='ux-erro-'+campo.id;let aviso=document.getElementById(id);
            if(!aviso){aviso=document.createElement('p');aviso.id=id;aviso.className='ux-field-error';const alvo=campo.parentElement.matches('.relative,.ux-password-wrap')?campo.parentElement:campo;alvo.after(aviso);}
            aviso.textContent=campo.validity.valueMissing?'Preencha este campo para continuar.':campo.validity.typeMismatch?'Digite um e-mail válido.':campo.validity.tooShort?`Use pelo menos ${campo.minLength} caracteres.`:'Confira o valor deste campo.';
            campo.setAttribute('aria-invalid','true');campo.setAttribute('aria-describedby',[...new Set([...(campo.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean),id])].join(' '));
        },true);
        document.addEventListener('input',evento=>{
            const campo=evento.target;if(!campo.id||!campo.validity?.valid)return;
            const id='ux-erro-'+campo.id;if(!document.getElementById(id))return;
            document.getElementById(id).remove();campo.removeAttribute('aria-invalid');
            const outros=(campo.getAttribute('aria-describedby')||'').split(/\s+/).filter(v=>v&&v!==id);if(outros.length)campo.setAttribute('aria-describedby',outros.join(' '));else campo.removeAttribute('aria-describedby');
        });
    },
    iniciar(){
        this.formularios();
        if(document.getElementById('loginAlunoScreen')){
            this.senha('loginSenhaAluno');this.senha('cadSenha');this.senha('recSenha');
            document.getElementById('loginAlunoScreen').addEventListener('submit',()=>this.limparFeedback(),true);
            this.aba(typeof abaAtiva!=='undefined'?abaAtiva:'catalogo');
        }
    }
};
document.addEventListener('DOMContentLoaded',()=>ExperienciaUI.iniciar());
