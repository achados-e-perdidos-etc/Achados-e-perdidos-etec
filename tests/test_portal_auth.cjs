const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('script.js', 'utf8');
function setup(fetch, email = 'professor', password = 'professor') {
  const values = new Map();
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {value: '', innerText: '', disabled: false, classList: {add(){}, remove(){}}});
    return elements.get(id);
  };
  element('loginEmailAluno').value = email;
  element('loginSenhaAluno').value = password;
  let sessions = 0;
  const ctx = vm.createContext({API_URL: 'http://localhost', fetch,
    document: {getElementById: element}, mostrarToast(){},
    localStorage: {setItem(k,v){values.set(k,v);}},
    checarSessao(){sessions++;}});
  ctx.iniciarAnimacaoAuth=()=>true;ctx.confirmarAnimacaoAuth=async()=>{};ctx.encerrarAnimacaoAuth=()=>{};
  ctx.SessaoPortal={token:()=>values.get('aluno_token'),dados:()=>JSON.parse(values.get('aluno_dados')||'null'),salvar(token,dados){values.set('aluno_token',token.trim());values.set('aluno_dados',JSON.stringify(dados));}};
  const start = source.indexOf('async function fazerLoginAluno(');
  const end = source.indexOf('async function confirmarCadastro(', start);
  vm.runInContext(source.slice(start, end), ctx);
  return {ctx, values, element, sessions: () => sessions};
}
test('credenciais compartilhadas rejeitadas não criam sessão', async () => {
  const ui = setup(async () => ({ok:false, json:async () => ({success:false})}));
  await ui.ctx.fazerLoginAluno({preventDefault(){}});
  assert.equal(ui.values.size, 0);
  assert.equal(ui.sessions(), 0);
  assert.equal(ui.element('btnAcessoLogin').disabled, false);
});
test('falha de rede não fabrica token de professor', async () => {
  const ui = setup(async () => {throw Error('offline');});
  await ui.ctx.fazerLoginAluno({preventDefault(){}});
  assert.equal(ui.values.size, 0);
  assert.equal(ui.sessions(), 0);
});
test('professor usa senha sem converter maiúsculas e sessão do servidor', async () => {
  let sent;
  const ui = setup(async (url, opts) => {
    sent = JSON.parse(opts.body);
    return {ok:true, json:async () => ({success:true, token:'token-assinado', aluno:{email:sent.email}})};
  }, 'docente@cps.sp.gov.br', 'MinhaSenhaABC!');
  await ui.ctx.fazerLoginAluno({preventDefault(){}});
  assert.equal(sent.senha, 'MinhaSenhaABC!');
  assert.equal(ui.values.get('aluno_token'), 'token-assinado');
  assert.equal(ui.sessions(), 1);
});
test('código de cadastro aceita domínios de professores e rejeita domínio falso', async () => {
  for (const email of ['docente@cps.sp.gov.br','docente@etec.sp.gov.br','docente@cps.sp.gov.br.falso.com']) {
    let calls=0;
    const ui=setup(async () => {calls++;return {ok:true,json:async()=>({success:false})};});
    ui.element('email').value=email;
    await ui.ctx.enviarCodigoAuth('email','button','show','hide');
    assert.equal(calls, email.endsWith('falso.com') ? 0 : 1);
  }
});
test('sessão fictícia antiga é removida antes de consultar o servidor', async () => {
  const ui = setup(async () => {throw Error('não deve chamar a rede');});
  ui.values.set('aluno_token','token_prof_123');
  ui.values.set('aluno_dados',JSON.stringify({rm:'PROFESSOR'}));
  ui.ctx.localStorage.getItem = key => ui.values.get(key);
  ui.ctx.fazerLogoff = () => ui.values.clear();
  const start = source.indexOf('async function checarSessao(');
  const end = source.indexOf('function fazerLogoff(',start);
  vm.runInContext(source.slice(start,end),ui.ctx);
  await ui.ctx.checarSessao();
  assert.equal(ui.values.size,0);
});
