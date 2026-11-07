"""Fluxos de acesso com HTML real, APIs simuladas e armazenamento do Chromium."""
import unittest
import browser_text_safety as safety


class LoginTests(safety.TextSafetyBrowser):
    def open_login(self):
        self.open()
        self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate('''() => {
            document.getElementById('loginAlunoScreen').classList.remove('hidden');
            window.fetch=async(url)=> {
                if(url.includes('/login-aluno') || url.includes('/cadastrar')) {
                    window._requests=(window._requests||0)+1;
                    return new Promise(resolve=>window._finish=resolve);
                }
                return {ok:true,status:200,json:async()=>[]};
            };
        }''')

    def start(self, signup=False, remember=False):
        self.page.evaluate('''({signup,remember})=>{
            if(signup) { alternarTelaAuth('cadastro'); document.getElementById('passo1Cadastro').classList.add('hidden');document.getElementById('passo2Cadastro').classList.remove('hidden'); }
            const fields=signup?{cadEmailAluno:'teste@aluno.cps.sp.gov.br',cadNome:'Aluno Teste',cadRM:'12345',cadCodigo:'123456',cadSenha:'SenhaTeste123!'}:{loginEmailAluno:'teste@aluno.cps.sp.gov.br',loginSenhaAluno:'SenhaTeste123!'};
            for(const [id,value] of Object.entries(fields))document.getElementById(id).value=value;
            document.getElementById(signup?'lembrarCadastro':'lembrarLogin').checked=remember;
            window._pending=(signup?confirmarCadastro:fazerLoginAluno)({preventDefault(){}});
        }''',dict(signup=signup,remember=remember))

    def finish(self, success=True):
        self.page.evaluate('''success=>window._finish({ok:success,status:success?200:401,json:async()=>success?{success:true,token:'sessao-real-teste',aluno:{nome:'Aluno Teste',email:'teste@aluno.cps.sp.gov.br',rm:'12345'}}:{success:false,message:'Credenciais incorretas'}})''',success)
        self.page.evaluate('window._pending')

    def test_auth_session_without_remember_and_no_duplicate_submit(self):
        self.open_login();self.start()
        self.assertTrue(self.page.locator('#authTransition').is_visible())
        self.assertTrue(self.page.locator('#formLoginAluno').evaluate('el=>el.inert'))
        self.page.evaluate('fazerLoginAluno({preventDefault(){}})')
        self.assertEqual(self.page.evaluate('window._requests'),1)
        self.finish()
        self.assertIsNone(self.page.evaluate("localStorage.getItem('aluno_token')"))
        self.assertEqual(self.page.evaluate("sessionStorage.getItem('aluno_token')"),'sessao-real-teste')
        self.assertFalse(self.page.locator('#authTransition').is_visible())
        self.assertEqual(self.page.locator('#loginSenhaAluno').input_value(),'')
        other=self.context.new_page();other.goto(safety.ORIGIN+'/index.html')
        self.assertIsNone(other.evaluate("sessionStorage.getItem('aluno_token')"))
        other.close()

    def test_auth_remember_restores_in_new_tab_and_logout_clears_both(self):
        self.open_login();self.start(remember=True);self.finish()
        self.assertEqual(self.page.evaluate("localStorage.getItem('aluno_token')"),'sessao-real-teste')
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem('aluno_token')"))
        other=self.context.new_page();other.goto(safety.ORIGIN+'/index.html')
        self.assertEqual(other.evaluate('SessaoPortal.token()'),'sessao-real-teste');other.close()
        self.page.evaluate('fazerLogoff(false)')
        self.assertIsNone(self.page.evaluate('SessaoPortal.token()'))
        self.assertIsNone(self.page.evaluate("localStorage.getItem('aluno_dados')"))

    def test_auth_signup_and_rejection_restore_form(self):
        self.open_login();self.start(signup=True)
        self.assertEqual(self.page.locator('#authTransitionTitulo').text_content(),'Preparando seu espaço')
        self.finish(False)
        self.assertFalse(self.page.locator('#authTransition').is_visible())
        self.assertFalse(self.page.locator('#formCadastroAluno').evaluate('el=>el.inert'))
        self.assertIsNone(self.page.evaluate('SessaoPortal.token()'))
        self.start(signup=True,remember=True);self.finish()
        self.assertEqual(self.page.evaluate("localStorage.getItem('aluno_lembrar')"),'true')
        self.assertEqual(self.page.locator('#cadSenha').input_value(),'')

    def test_auth_network_failure_and_reduced_motion(self):
        self.open_login();self.page.emulate_media(reduced_motion='reduce');self.start()
        self.assertEqual(self.page.locator('.auth-orbit-ring-outer').evaluate('el=>getComputedStyle(el).animationName'),'none')
        self.page.evaluate("window._finish(Promise.reject(Error('offline')))")
        self.page.evaluate('window._pending')
        self.assertFalse(self.page.locator('#authTransition').is_visible())
        self.assertIsNone(self.page.evaluate('SessaoPortal.token()'))
        self.assertFalse(self.page.locator('#formLoginAluno').evaluate('el=>el.inert'))

    def test_auth_legacy_is_session_only_and_teacher_panel_respects_storage(self):
        self.open_login()
        self.page.evaluate('''()=>{localStorage.setItem('aluno_token','legado');localStorage.setItem('aluno_dados',JSON.stringify({nome:'Legado',email:'legado@etec.sp.gov.br'}));SessaoPortal.token();SessaoPortal.compartilharPainel();}''')
        self.assertIsNone(self.page.evaluate("localStorage.getItem('aluno_token')"))
        self.assertEqual(self.page.evaluate("sessionStorage.getItem('secretaria_token')"),'legado')
        self.page.evaluate("SessaoPortal.salvar('lembrado',{nome:'Docente',email:'docente@etec.sp.gov.br'},true);SessaoPortal.compartilharPainel()")
        self.assertEqual(self.page.evaluate("localStorage.getItem('secretaria_token')"),'lembrado')
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem('secretaria_token')"))


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(LoginTests(name) for name in loader.getTestCaseNames(LoginTests) if name.startswith('test_auth_'))

if __name__=='__main__':unittest.main(verbosity=2)
