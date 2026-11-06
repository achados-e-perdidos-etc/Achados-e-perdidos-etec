const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const helper=fs.readFileSync('visao-formulario.js','utf8');
function fields() {
 return {nome:{value:'Nome manual'},descricao:{value:'Descrição manual'},categoria:{value:'ROUPAS',options:[{value:'ROUPAS'},{value:'MOCHILA'},{value:'ELETRONICOS'},{value:'OUTROS'}]}};
}
const valid=()=>({metodo:'gemini_vision_ocr',pode_preencher:true,confianca_objeto:'alta',nome:'Mochila azul',descricao:'Mochila com zíper',categoria:'MOCHILA'});
function setup() {const ctx=vm.createContext({});vm.runInContext(helper,ctx);return ctx;}
test('categoria MOCHILA preserva letras e seleciona a opção correta',()=>{
 const ctx=setup(), f=fields();assert.equal(ctx.aplicarSugestaoVisual(valid(),f),true);assert.equal(f.categoria.value,'MOCHILA');
});
test('categoria com acento corresponde à versão sem acento',()=>{
 const ctx=setup(), f=fields();ctx.aplicarSugestaoVisual({...valid(),categoria:'ELETRÔNICOS'},f);assert.equal(f.categoria.value,'ELETRONICOS');
});
test('categoria vazia ou desconhecida não seleciona a primeira opção',()=>{
 const ctx=setup();for(const categoria of ['', 'ROUPA'] ) {
  const f=fields();f.categoria.value='OUTROS';ctx.aplicarSugestaoVisual({...valid(),categoria},f);assert.equal(f.categoria.value,'OUTROS');
 }
});
test('fallback e baixa confiança preservam todos os campos',()=>{
 const ctx=setup();for(const change of [{pode_preencher:false},{confianca_objeto:'baixa'},{metodo:'visao_local_fallback'},{nome:[]},{descricao:''}]){
  const f=fields();assert.equal(ctx.aplicarSugestaoVisual({...valid(),...change},f),false);
  assert.equal(f.nome.value,'Nome manual');assert.equal(f.descricao.value,'Descrição manual');assert.equal(f.categoria.value,'ROUPAS');
 }
});
function portal(response, deferred) {
 const f=fields();const ui={alunoItemNome:f.nome,alunoItemDesc:f.descricao,alunoItemCat:f.categoria,btnAutoPreencherIAAluno:{disabled:false,innerHTML:''}};
 const messages=[];const photos=['foto-A'];
 const ctx=vm.createContext({API_URL:'https://exemplo',fotosAlunoSelecionadas:photos,
  document:{getElementById:id=>ui[id]},mostrarToast:(...args)=>messages.push(args),
  fetch:deferred|| (async()=>({ok:true,json:async()=>({success:true,resultado:response})}))});
 vm.runInContext(helper,ctx);const js=fs.readFileSync('script.js','utf8');vm.runInContext(js.slice(js.indexOf('async function analisarFotoAlunoComIA(')),ctx);
 return {ctx,f,messages,photos};
}
test('portal não anuncia preenchimento nem sobrescreve campos no fallback',async()=>{
 const p=portal({...valid(),pode_preencher:false,aviso:'Preencha manualmente'});await p.ctx.analisarFotoAlunoComIA();
 assert.equal(p.f.nome.value,'Nome manual');assert.equal(p.messages[0][1],'info');assert.equal(p.messages[0][0],'Preencha manualmente');
});
test('análise de foto antiga não preenche o formulário da foto nova',async()=>{
 let complete;const p=portal(valid(),()=>new Promise(resolve=>{complete=resolve;}));const pending=p.ctx.analisarFotoAlunoComIA();
 p.photos[0]='foto-B';complete({ok:true,json:async()=>({success:true,resultado:valid()})});await pending;
 assert.equal(p.f.nome.value,'Nome manual');assert.equal(p.messages.length,0);
});
test('painel da secretaria não usa OCR nem apaga dados manuais em fallback',async()=>{
 const f=fields(), ui={formItemNome:f.nome,formItemDescricao:f.descricao,formItemCategoria:f.categoria,formFotosStatus:{innerText:''},btnAutoTagIA:{disabled:false,innerHTML:''}};
 const ctx=vm.createContext({fotosBase64Upload:['foto-A'],ocrRmIdentificado:'rm-antigo',
  document:{getElementById:id=>ui[id]},console,alert(){},
  fetch:async()=>({ok:true,json:async()=>({success:true,resultado:{...valid(),pode_preencher:false,aviso:'Análise indisponível',ocr_rm:'12345'}})})});
 vm.runInContext(helper,ctx);const html=fs.readFileSync('controle_etec_7788.html','utf8');const start=html.lastIndexOf('async function analisarFotoSecretariaComIA(');
 vm.runInContext(html.slice(start,html.indexOf('</script>',start)),ctx);await ctx.analisarFotoSecretariaComIA();
 assert.equal(f.nome.value,'Nome manual');assert.equal(f.descricao.value,'Descrição manual');assert.equal(ctx.ocrRmIdentificado,'');assert.equal(ui.formFotosStatus.innerText,'Análise indisponível');
});
