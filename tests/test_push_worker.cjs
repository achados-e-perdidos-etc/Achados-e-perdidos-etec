const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
function setup(){
 const handlers={},notices=[],opened=[],navigated=[];
 const client={async navigate(url){navigated.push(url);},async focus(){return true;}};
 const ctx=vm.createContext({URL,self:{location:{origin:'https://escola.example.org'},addEventListener:(name,fn)=>handlers[name]=fn,registration:{async showNotification(title,options){notices.push({title,options});}}},
 clients:{async matchAll(){return [client];},async openWindow(url){opened.push(url);}}});
 vm.runInContext(fs.readFileSync('sw.js','utf8'),ctx);
 return {handlers,notices,opened,navigated,ctx};
}
test('push recebido mostra aviso e abrir usa o próprio portal',async()=>{
 const p=setup();let pending;
 p.handlers.push({data:{json:()=>({title:'Nova mensagem',body:'Abra o portal',url:'/'})},waitUntil:x=>pending=x});await pending;
 assert.equal(p.notices[0].title,'Nova mensagem');assert.equal(p.notices[0].options.body,'Abra o portal');
 p.handlers.notificationclick({action:'abrir',notification:{close(){},data:p.notices[0].options.data},waitUntil:x=>pending=x});await pending;
 assert.deepEqual(p.navigated,['https://escola.example.org/']);
});
test('URL e ícone externos não redirecionam nem carregam recursos de terceiros',async()=>{
 const p=setup();let pending;
 p.handlers.push({data:{json:()=>({title:'Teste',body:'Teste',url:'https://outra.example.org/',icon:'https://outra.example.org/a.png'})},waitUntil:x=>pending=x});await pending;
 assert.equal(p.notices[0].options.icon,'/icon-192.png');assert.equal(p.notices[0].options.data.url,'https://escola.example.org/');
});
test('dispensar não abre nem navega',()=>{
 const p=setup();let closed=false;
 p.handlers.notificationclick({action:'fechar',notification:{close(){closed=true;},data:{url:'/'}},waitUntil(){throw Error('não deve navegar');}});
 assert.equal(closed,true);assert.equal(p.opened.length,0);assert.equal(p.navigated.length,0);
});
test('payload inesperado recebe texto seguro e limitado',async()=>{
 const p=setup();let pending;
 p.handlers.push({data:{json:()=>({title:{x:1},body:[],url:'javascript:alert(1)'})},waitUntil:x=>pending=x});await pending;
 assert.equal(typeof p.notices[0].title,'string');assert.equal(typeof p.notices[0].options.body,'string');assert.equal(p.notices[0].options.data.url,'https://escola.example.org/');
});
