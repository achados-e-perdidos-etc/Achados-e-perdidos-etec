const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(email='docente@etec.sp.gov.br') {
 const elements=new Map();
 function el(id) {
  if(!elements.has(id)) {
   const classes=new Set();
   elements.set(id,{disabled:false,textContent:'',classList:{
    add(x){classes.add(x);},remove(x){classes.delete(x);},
    toggle(x,yes){if(yes===undefined)yes=!classes.has(x);yes?classes.add(x):classes.delete(x);},
    contains(x){return classes.has(x);}}});
  }
  return elements.get(id);
 }
 let status='PENDENTE'; const calls=[]; const values=new Map([['aluno_token','sessao-do-professor']]);let destination;
 const ctx=vm.createContext({API_URL:'https://escola.exemplo',alunoSessao:{email},
  document:{getElementById:el},mostrarToast(){},URL,
  localStorage:{getItem(k){return values.get(k);},setItem(k,v){values.set(k,v);}},
  window:{location:{origin:'https://escola.exemplo',assign(url){destination=url;}}},
  fetch:async(url,opts)=>{calls.push({url,opts});return {ok:status!=='ERRO',json:async()=>({success:status!=='ERRO',status})};}});
 ctx.SessaoPortal={token:()=>values.get('aluno_token'),compartilharPainel(){values.set('secretaria_token',values.get('aluno_token'));}};
 vm.runInContext(fs.readFileSync('professores.js','utf8'),ctx);
 return {ctx,el,calls,values,status(x){status=x;},destination:()=>destination};
}
test('conta de aluno não oferece pedido de acesso',async()=>{
 const ui=setup('aluno@aluno.cps.sp.gov.br');
 await ui.ctx.atualizarAcessoProfessor();
 assert.equal(ui.calls.length,0);
 assert.equal(ui.el('acessoProfessor').classList.contains('hidden'),true);
});
test('pedido pendente aparece aguardando aprovação e impede abrir painel',async()=>{
 const ui=setup();await ui.ctx.atualizarAcessoProfessor();
 assert.match(ui.el('statusAcessoProfessor').textContent,/aguarda/);
 assert.equal(ui.el('btnSolicitarAcessoProfessor').disabled,true);
 await ui.ctx.abrirPainelProfessor();assert.equal(ui.destination(),undefined);
});
test('solicitação envia somente sessão e atualiza status',async()=>{
 const ui=setup();await ui.ctx.solicitarAcessoProfessor();
 assert.equal(ui.calls[0].opts.method,'POST');
 assert.equal(ui.calls[0].opts.headers.Authorization,'Bearer sessao-do-professor');
 assert.equal(ui.calls[0].opts.body,undefined);
 assert.equal(ui.calls.length,2);
});
test('aprovado entra pelo token pessoal e revogação impede entrada',async()=>{
 const ui=setup();ui.status('APROVADO');await ui.ctx.abrirPainelProfessor();
 assert.equal(ui.destination(),'https://escola.exemplo/secretaria');
 assert.equal(ui.values.get('secretaria_token'),'sessao-do-professor');
 const revoked=setup();revoked.status('APROVADO');await revoked.ctx.atualizarAcessoProfessor();
 revoked.status('REVOGADO');await revoked.ctx.abrirPainelProfessor();
 assert.equal(revoked.destination(),undefined);
 assert.equal(revoked.el('btnAbrirPainelProfessor').classList.contains('hidden'),true);
});
test('erro na consulta oculta acesso mesmo após aprovação anterior',async()=>{
 const ui=setup();ui.status('APROVADO');await ui.ctx.atualizarAcessoProfessor();
 ui.status('ERRO');await ui.ctx.atualizarAcessoProfessor();
 assert.equal(ui.el('btnAbrirPainelProfessor').classList.contains('hidden'),true);
 assert.equal(ui.el('btnSolicitarAcessoProfessor').disabled,true);
});
