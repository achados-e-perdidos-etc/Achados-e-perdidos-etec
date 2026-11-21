/* A apresentação nunca segura a autenticação nem exige baixar uma animação inteira. */
const AberturaPortal={
    iniciada:false,encerrada:false,timer:null,
    iniciar(){
        if(this.iniciada)return;this.iniciada=true;
        const box=document.getElementById('splashScreenAnimacao'),video=document.getElementById('videoAbertura');
        let exibida=true;try{exibida=sessionStorage.getItem('splash_ja_exibido')==='true';sessionStorage.setItem('splash_ja_exibido','true');}catch(_){}
        const conexao=navigator.connection;
        if(!box||!video||exibida||!navigator.onLine||conexao?.saveData||['slow-2g','2g'].includes(conexao?.effectiveType)||window.matchMedia('(prefers-reduced-motion: reduce)').matches){this.encerrar();checarSessao();return;}
        box.hidden=false;
        document.getElementById('pularAbertura').onclick=()=>this.encerrar();
        this.timer=setTimeout(()=>this.encerrar(),2400);
        video.onended=video.onerror=()=>this.encerrar();
        video.src=window.matchMedia('(orientation: landscape)').matches?'abertura-computador.mp4':'abertura-celular.mp4';
        video.play().catch(()=>this.encerrar());
        window.addEventListener('offline',()=>this.encerrar(),{once:true});
        checarSessao();
    },
    encerrar(){
        if(this.encerrada)return;this.encerrada=true;clearTimeout(this.timer);
        const box=document.getElementById('splashScreenAnimacao'),video=document.getElementById('videoAbertura');
        if(box)box.hidden=true;
        if(video){video.onended=video.onerror=null;video.pause();video.removeAttribute('src');video.load();}
    }
};
document.addEventListener('DOMContentLoaded',()=>AberturaPortal.iniciar(),{once:true});
