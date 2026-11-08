// Estado real da preparação/envio, sem porcentagem simulada nem espera artificial.
function mostrarEstadoFotos(id, estado, mensagem) {
 const box=document.getElementById(id); if(!box)return;
 box.hidden=false;box.className='estado-fotos';box.dataset.estado=estado;
 box.setAttribute('role','status');box.setAttribute('aria-live','polite');box.setAttribute('aria-atomic','true');
 box.setAttribute('aria-busy',String(['preparando','enviando'].includes(estado)));
 const icone=document.createElement('span');icone.className='estado-fotos-icone';icone.setAttribute('aria-hidden','true');
 const texto=document.createElement('span');texto.textContent=mensagem;box.replaceChildren(icone,texto);
}
function ocultarEstadoFotos(id) {const box=document.getElementById(id);if(box)box.hidden=true;}
function comprimirImagem(arquivo,maxDim=1200,qualidade=.75) {
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();reader.onerror=()=>reject(Error('Não foi possível ler a foto.'));
  reader.onload=e=>{
   const img=new Image();img.onerror=()=>reject(Error('Não foi possível abrir a foto.'));
   img.onload=()=>{try {
    const escala=Math.min(1,maxDim/Math.max(img.width,img.height)),canvas=document.createElement('canvas');
    canvas.width=Math.max(1,Math.round(img.width*escala));canvas.height=Math.max(1,Math.round(img.height*escala));
    canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',qualidade));
   }catch(error){reject(error);}};
   img.src=e.target.result;
  };reader.readAsDataURL(arquivo);
 });
}
