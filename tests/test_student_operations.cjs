const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('script.js','utf8');

function portal(name,next) {
 const calls=[];
 const ui={alunoItemFoto:{},gridPreviewAluno:{},btnAutoPreencherIAAluno:{},btnNovo:{},btnPublicarMural:{},btnSalvarAlunoItem:{},
  muralCategoria:{value:'OUTROS'},muralDescricao:{value:'  Perdi meu estojo  '},
  alunoItemNome:{value:'  Estojo preto  '},alunoItemDesc:{value:'  Encontrado  '},
  alunoItemCat:{value:'OUTROS'},alunoItemLocal:{value:'  Pátio  '}};
 const ctx=vm.createContext({API_URL:'https://exemplo',itemSelecionado:{id:7},
  alunoSessao:{nome:'Nome armazenado no navegador',rm:'99999',email:'outro@aluno.cps.sp.gov.br'},
  envioCadastroAluno:false,preparandoFotosAluno:false,mostrarEstadoFotos(){},fotosAlunoSelecionadas:[],localStorage:{getItem:()=> 'sessao-assinada'},
  document:{getElementById:id=>ui[id]},mostrarToast(){},
  fetch:async(url,options)=>{calls.push({url,options});return {ok:false,json:async()=>({success:false,message:'Teste'})};}});
 const start=source.indexOf(`async function ${name}(`);
 const end=source.indexOf(next,start);
 assert.ok(start>=0&&end>start);
 ctx.SessaoPortal={token:()=>ctx.localStorage.getItem('aluno_token')};
 vm.runInContext(source.slice(start,end),ctx);
 return {ctx,calls};
}

test('solicitação envia sessão e ID sem escolher identidade pelo navegador',async()=>{
 const {ctx,calls}=portal('enviarNovo','async function enviarAvisoMural(');
 await ctx.enviarNovo();
 assert.equal(calls.length,1);
 assert.equal(calls[0].options.headers.Authorization,'Bearer sessao-assinada');
 assert.deepEqual(JSON.parse(calls[0].options.body),{id:7});
});

test('mural envia conteúdo e sessão sem nome, RM ou e-mail de autoria',async()=>{
 const {ctx,calls}=portal('enviarAvisoMural','async function carregarMuralPublico(');
 await ctx.enviarAvisoMural({preventDefault(){}});
 assert.equal(calls.length,1);
 assert.equal(calls[0].options.headers.Authorization,'Bearer sessao-assinada');
 assert.deepEqual(JSON.parse(calls[0].options.body),{categoria:'OUTROS',descricao:'Perdi meu estojo'});
});

test('cadastro conserva o nome do objeto e não envia RM de autoria',async()=>{
 const {ctx,calls}=portal('enviarCadastroAluno','window.onload =');
 await ctx.enviarCadastroAluno({preventDefault(){}});
 assert.equal(calls.length,1);
 assert.equal(calls[0].options.headers.Authorization,'Bearer sessao-assinada');
 const body=JSON.parse(calls[0].options.body);
 assert.equal(body.nome,'Estojo preto');
 assert.equal(body.descricao,'Encontrado');
 assert.equal(body.local,'Pátio');
 assert.equal(Object.hasOwn(body,'rm'),false);
 assert.equal(Object.hasOwn(body,'email'),false);
});
