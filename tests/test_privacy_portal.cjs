const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
test('Meus itens usa sessão e consulta privada sem depender de nome ou RM retornados',async()=>{
 const source=fs.readFileSync('script.js','utf8');
 const calls=[];
 const elements={listaMinhasSolicitacoes:{innerHTML:''},listaMeusRelatosMural:{innerHTML:''}};
 const ctx=vm.createContext({API_URL:'https://exemplo',alunoSessao:{rm:'12345',nome:'Nome repetido'},
  mudarAba(){},localStorage:{getItem(){return 'sessao-valida';}},
  document:{getElementById(id){return elements[id];}},normalizarStatus(){return 'SOLICITADO';},
  fetch:async(url,opts)=>{
   calls.push({url,opts});
   return {ok:true,json:async()=>url.includes('/api/itens/meus')?[{id:7,nome:'Meu Estojo',status:'SOLICITADO'}]:[]};
  }});
 const start=source.indexOf('async function abrirPainelMeusItens(');
 const end=source.indexOf('function selecionarFiltroCategoria(',start);
 ctx.SessaoPortal={token:()=>ctx.localStorage.getItem('aluno_token')};
 vm.runInContext(fs.readFileSync('seguranca-interface.js','utf8'),ctx);
 vm.runInContext(source.slice(start,end),ctx);
 await ctx.abrirPainelMeusItens();
 assert.equal(calls.length,2);
 assert.equal(calls[0].url,'https://exemplo/api/itens/meus');
 for(const call of calls)assert.equal(call.opts.headers.Authorization,'Bearer sessao-valida');
 assert.match(elements.listaMinhasSolicitacoes.innerHTML,/Meu Estojo/);
});
