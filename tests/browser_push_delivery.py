"""Botão de teste: APIs e PushManager simulados, página real."""
import unittest
import browser_text_safety as safety


class PushTest(safety.TextSafetyBrowser):
    def prepare(self, ok=True):
        self.open();self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate('''ok=>{
            document.getElementById('loginAlunoScreen').classList.add('hidden');
            document.getElementById('perfilMenu').classList.remove('hidden');
            SessaoPortal.salvar('sessao-teste',{nome:'Aluno',email:'aluno@aluno.cps.sp.gov.br',rm:'12345'});
            Object.defineProperty(window,'Notification',{value:{permission:'granted'},configurable:true});
            const sub={endpoint:'https://fcm.googleapis.com/teste',toJSON(){return {endpoint:this.endpoint,keys:{auth:'fake',p256dh:'fake'}}}};
            const reg={pushManager:{async getSubscription(){return sub}}};
            Object.defineProperty(navigator.serviceWorker,'ready',{value:Promise.resolve(reg),configurable:true});
            navigator.serviceWorker.getRegistration=async()=>reg;
            window._calls=[];
            window.fetch=async(url,opts)=>{
                window._calls.push({url,opts});
                if(url.endsWith('/test'))return new Promise(resolve=>window._done=resolve);
                return {ok:true,json:async()=>url.endsWith('/public-key')?{success:true,publicKey:'BAAA'}:{success:true}};
            };
        }''',ok)

    def test_push_button_uses_session_and_waits_without_claiming_delivery(self):
        self.prepare()
        self.page.evaluate('()=>{window._pending=testarNotificacaoPush();}')
        self.page.wait_for_function('window._done!==undefined')
        self.assertTrue(self.page.locator('#btnTestarPush').is_disabled())
        self.page.evaluate('testarNotificacaoPush()')
        self.assertEqual(self.page.evaluate("window._calls.filter(c=>c.url.endsWith('/test')).length"),1)
        self.page.evaluate("window._done({ok:true,json:async()=>({success:true,queued:true})})")
        self.page.evaluate('window._pending')
        self.assertFalse(self.page.locator('#btnTestarPush').is_disabled())
        self.assertIn('Teste solicitado',self.page.locator('#toastContainer').text_content())
        headers=self.page.evaluate("window._calls.find(c=>c.url.endsWith('/test')).opts.headers")
        self.assertEqual(headers['Authorization'],'Bearer sessao-teste')

    def test_push_server_rejection_restores_button_and_shows_message(self):
        self.prepare()
        self.page.evaluate('()=>{window._pending=testarNotificacaoPush();}')
        self.page.wait_for_function('window._done!==undefined')
        self.page.evaluate("window._done({ok:false,json:async()=>({success:false,message:'Aguarde 30 segundos.'})})")
        self.page.evaluate('window._pending')
        self.assertFalse(self.page.locator('#btnTestarPush').is_disabled())
        self.assertIn('Aguarde 30 segundos',self.page.locator('#toastContainer').text_content())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(PushTest(name) for name in loader.getTestCaseNames(PushTest) if name.startswith('test_push_'))

if __name__=='__main__':unittest.main(verbosity=2)
