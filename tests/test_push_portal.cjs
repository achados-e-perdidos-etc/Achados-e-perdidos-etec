const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('notificacoes-push.js','utf8');

function setup() {
 const storage=new Map([['aluno_token','sessao-A'],['aluno_dados','dados-A'],['secretaria_token','sessao-A']]);
 const calls=[];
 let unsubscribes=0,subscriptions=0,reloads=0;
 const sub={endpoint:'https://push.example.org/dispositivo',keys:{auth:'teste',p256dh:'teste'},
  async unsubscribe(){unsubscribes++;return true;},
  toJSON(){return {endpoint:this.endpoint,keys:this.keys};}};
 const registration={pushManager:{async getSubscription(){return sub;},
  async subscribe(options){subscriptions++;return sub;}}};
 const ctx=vm.createContext({API_URL:'https://etec.example.org',alunoSessao:{rm:'99999'},
  localStorage:{getItem:key=>storage.get(key),removeItem:key=>storage.delete(key)},
  navigator:{serviceWorker:{ready:Promise.resolve(registration),async getRegistration(){return registration;}}},
  Notification:{permission:'granted'},
  window:{PushManager(){},Notification:{},atob:s=>Buffer.from(s,'base64').toString('binary'),location:{reload(){reloads++;}}},
  document:{getElementById(){return {classList:{remove(){}}};}},
  setTimeout,fetch:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({success:true,publicKey:'BAAA'})};}});
 ctx.SessaoPortal={token:()=>storage.get('aluno_token'),limpar(){storage.clear();}};
 vm.runInContext(source,ctx);
 return {ctx,storage,calls,sub,registration,unsubscribes:()=>unsubscribes,subscriptions:()=>subscriptions,reloads:()=>reloads};
}

test('assinatura existente é recadastrada com sessão, sem escolher RM/e-mail',async()=>{
 const p=setup();
 assert.equal(await p.ctx.ativarWebPush(),true);
 assert.equal(p.calls.length,2);
 assert.equal(p.calls[1].options.headers.Authorization,'Bearer sessao-A');
 assert.deepEqual(JSON.parse(p.calls[1].options.body),{subscription:{endpoint:p.sub.endpoint,keys:p.sub.keys}});
 assert.equal(p.subscriptions(),0);
});

test('assinatura nova usa chave pública e não depende de RM',async()=>{
 const p=setup();p.registration.pushManager.getSubscription=async()=>null;
 assert.equal(await p.ctx.ativarWebPush(),true);
 assert.equal(p.subscriptions(),1);
 assert.equal(p.calls[0].url,'https://etec.example.org/api/push/public-key');
 assert.equal(p.calls[1].options.headers.Authorization,'Bearer sessao-A');
});

test('portal registra service worker ausente antes de aguardar assinatura',async()=>{
 const p=setup();const registrations=[];
 p.ctx.navigator.serviceWorker.getRegistration=async()=>null;
 p.ctx.navigator.serviceWorker.register=async path=>{registrations.push(path);return p.registration;};
 assert.equal(await p.ctx.ativarWebPush(),true);
 assert.deepEqual(registrations,['/sw.js']);
});

test('permissão concedida ou já existente inicia cadastro autenticado',async()=>{
 for(const permission of ['granted','default']){
  const p=setup();let activated=0;
  p.ctx.Notification.permission=permission;
  p.ctx.Notification.requestPermission=async()=> 'granted';
  p.ctx.ativarWebPush=()=>{activated++;};p.ctx.mostrarToast=()=>{};
  const js=fs.readFileSync('script.js','utf8');
  const start=js.indexOf('function solicitarPermissaoNotificacao('),end=js.indexOf('function dispararNotificacaoNativa(',start);
  vm.runInContext(js.slice(start,end),p.ctx);
  p.ctx.solicitarPermissaoNotificacao();await Promise.resolve();
  assert.equal(activated,1);
 }
});

test('sem sessão ou permissão não cadastra nem pede autorização automaticamente',async()=>{
 for(const variant of ['sem-token','sem-permissao']){
  const p=setup();
  if(variant==='sem-token')p.storage.clear();else p.ctx.Notification.permission='default';
  assert.equal(await p.ctx.ativarWebPush(),false);
  assert.equal(p.calls.length,0);assert.equal(p.subscriptions(),0);
 }
});

test('rejeição do servidor e falha de rede não são tratadas como sucesso',async()=>{
 for(const fetch of [async()=>({ok:false,json:async()=>({success:false})}),async()=>{throw Error('offline');}]){
  const p=setup();p.ctx.fetch=fetch;
  assert.equal(await p.ctx.ativarWebPush(),false);
 }
});

test('troca de token impede envio com sessão antiga',async()=>{
 const p=setup();p.storage.set('aluno_token','sessao-B');
 assert.equal(await p.ctx.enviarSubscricaoAoBackend(p.sub,'sessao-A'),false);
 assert.equal(p.calls.length,0);
});

test('logout durante espera do service worker impede cadastro atrasado',async()=>{
 const p=setup();let ready;
 p.ctx.navigator.serviceWorker.ready=new Promise(resolve=>{ready=resolve;});
 const pending=p.ctx.ativarWebPush();
 p.storage.clear();await p.ctx.desativarWebPush('sessao-A');
 ready(p.registration);assert.equal(await pending,false);
 assert.equal(p.calls.filter(c=>c.options.method==='POST').length,0);
 assert.equal(p.unsubscribes(),1);
});

test('assinatura criada depois do logout é cancelada e não enviada',async()=>{
 const p=setup();let subscribed,started;
 const entering=new Promise(resolve=>{started=resolve;});
 p.registration.pushManager.getSubscription=async()=>null;
 p.registration.pushManager.subscribe=()=>{started();return new Promise(resolve=>{subscribed=resolve;});};
 const pending=p.ctx.ativarWebPush();await entering;
 p.storage.clear();await p.ctx.desativarWebPush('sessao-A');
 subscribed(p.sub);assert.equal(await pending,false);
 assert.equal(p.unsubscribes(),1);
 assert.equal(p.calls.filter(c=>c.options?.method==='POST').length,0);
});

test('logout revoga assinatura no navegador e desvincula com token capturado',async()=>{
 const p=setup();p.storage.clear();
 await p.ctx.desativarWebPush('sessao-A');
 assert.equal(p.unsubscribes(),1);
 assert.equal(p.calls[0].options.method,'DELETE');
 assert.equal(p.calls[0].options.keepalive,true);
 assert.equal(p.calls[0].options.headers.Authorization,'Bearer sessao-A');
 assert.deepEqual(JSON.parse(p.calls[0].options.body),{endpoint:p.sub.endpoint});
});

test('logout offline ainda cancela assinatura local',async()=>{
 const p=setup();p.ctx.fetch=async()=>{throw Error('offline');};
 await p.ctx.desativarWebPush('sessao-A');
 assert.equal(p.unsubscribes(),1);
});

test('fazerLogoff limpa sessão imediatamente e aguarda limpeza antes de recarregar',async()=>{
 const p=setup();const js=fs.readFileSync('script.js','utf8');
 const start=js.indexOf('function fazerLogoff('),end=js.indexOf('function toggleMenuNavegacao(',start);
 vm.runInContext(js.slice(start,end),p.ctx);
 const pending=p.ctx.fazerLogoff();
 assert.equal(p.storage.size,0);assert.equal(p.ctx.alunoSessao,null);
 assert.equal(p.reloads(),0);
 await pending;assert.equal(p.reloads(),1);assert.equal(p.unsubscribes(),1);
});


test('rotação de chave VAPID recadastra assinatura incompatível',async()=>{
 const p=setup();p.sub.options={applicationServerKey:new Uint8Array([99,99]).buffer};
 assert.equal(await p.ctx.ativarWebPush(),true);
 assert.equal(p.unsubscribes(),1);assert.equal(p.subscriptions(),1);
});

test('configuração desabilitada não registra assinatura nem anuncia sucesso',async()=>{
 const p=setup();p.ctx.fetch=async()=>({ok:true,json:async()=>({success:false,habilitado:false,publicKey:''})});
 assert.equal(await p.ctx.ativarWebPush(),false);assert.equal(p.subscriptions(),0);
});

test('teste solicita apenas a própria conta e anuncia fila, sem afirmar entrega',async()=>{
 const p=setup();const btn={disabled:false},messages=[];p.ctx.document.getElementById=()=>btn;
 p.ctx.mostrarToast=text=>messages.push(text);
 p.ctx.fetch=async(url,opts)=>{p.calls.push({url,options:opts});return {ok:true,json:async()=>url.endsWith('/test')?{success:true,queued:true}:{success:true,publicKey:'BAAA'}};};
 await p.ctx.testarNotificacaoPush();
 const call=p.calls.find(c=>c.url.endsWith('/test'));
 assert.equal(call.options.headers.Authorization,'Bearer sessao-A');assert.equal(call.options.body,undefined);
 assert.match(messages[0],/solicitado/);assert.equal(btn.disabled,false);
});
