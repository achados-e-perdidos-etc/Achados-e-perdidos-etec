"""Transições nas páginas reais, sem alterar fluxo ou comunicação externa."""
import unittest
import browser_text_safety as safety


class MotionTests(safety.TextSafetyBrowser):
    def portal(self):
        self.open();self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate("document.getElementById('loginAlunoScreen').classList.add('hidden')")

    def animation(self, selector):
        return self.page.locator(selector).evaluate('el=>getComputedStyle(el).animationName')

    def test_motion_portal_sections_menus_and_modal_close_immediately(self):
        self.portal()
        self.page.evaluate("mudarAba('mural')")
        self.assertEqual(self.animation('#muralScreen'),'movimento-secao')
        self.assertTrue(self.page.locator('#catalogScreen').evaluate("el=>el.classList.contains('hidden')"))
        self.page.evaluate('toggleMenuNavegacao()')
        self.assertEqual(self.animation('#menuNavegacaoDropdown'),'movimento-menu')
        self.page.evaluate('fecharMenuNavegacao()')
        self.assertEqual(self.page.locator('#menuNavegacaoDropdown').evaluate('el=>getComputedStyle(el).display'),'none')
        self.page.evaluate('abrirModalCadastrarAluno()')
        self.assertEqual(self.animation('#modalCadastrarAluno > .glass-panel'),'movimento-modal')
        self.page.evaluate("document.getElementById('modalCadastrarAluno').classList.add('hidden')")
        self.assertEqual(self.page.locator('#modalCadastrarAluno').evaluate('el=>getComputedStyle(el).display'),'none')

    def test_motion_panel_modal_and_sections_preserve_layout_after_animation(self):
        self.open(admin=True)
        self.page.evaluate("trocarAba('categorias')")
        self.assertEqual(self.animation('#secao-categorias'),'movimento-secao')
        self.page.evaluate('abrirModalCadastrar()')
        self.assertEqual(self.animation('#modalFormItem > .modal-box'),'movimento-modal')
        self.page.wait_for_timeout(320)
        self.assertEqual(self.page.locator('#modalFormItem > .modal-box').evaluate('el=>getComputedStyle(el).transform'),'none')
        self.assertEqual(self.page.locator('#secao-categorias').evaluate('el=>getComputedStyle(el).transform'),'none')
        self.page.evaluate("fecharModal('modalFormItem')")
        self.assertFalse(self.page.locator('#modalFormItem').is_visible())

    def test_motion_cards_are_bounded_and_chat_messages_do_not_reanimate(self):
        self.portal()
        self.page.evaluate("()=>{todosItens=Array.from({length:12},(_,i)=>({id:i,nome:'Estojo',categoria:'OUTROS',status:'DISPONÍVEL'}));renderizarItens();alunoSessao={rm:'12345'};ultimaQtdMensagens=0;}")
        self.assertEqual(self.animation('#itemsGrid > div:first-child'),'movimento-card')
        delays=self.page.locator('#itemsGrid > div').evaluate_all('els=>els.map(el=>parseFloat(getComputedStyle(el).animationDelay))')
        self.assertLessEqual(max(delays),.09)
        self.fixture([dict(remetente='SECRETARIA',mensagem='Olá')])
        self.page.evaluate('atualizarMensagensChat()')
        self.assertEqual(self.animation('#chatMensagens > div'),'none')
        self.page.wait_for_timeout(320)
        self.assertEqual(self.page.locator('#itemsGrid > div').first.evaluate('el=>getComputedStyle(el).transform'),'none')

    def test_motion_reduced_preference_disables_new_and_old_css_and_carousel_smooth_scroll(self):
        self.page.emulate_media(reduced_motion='reduce');self.portal()
        self.page.evaluate('abrirModalCadastrarAluno()')
        self.assertEqual(self.animation('#modalCadastrarAluno > .glass-panel'),'none')
        self.assertEqual(self.page.locator('#btnSalvarAlunoItem').evaluate('el=>getComputedStyle(el).transitionDuration'),'0s')
        self.page.evaluate("()=>{fotosAtuais=['a','b'];fotoIndiceAtual=0;document.getElementById('carouselContainer').scrollTo=opts=>window._scrollBehavior=opts.behavior;navegarFotos(1);}")
        self.assertEqual(self.page.evaluate('window._scrollBehavior'),'auto')
        self.open(admin=True);self.page.evaluate('abrirModalCadastrar()')
        self.assertEqual(self.animation('#modalFormItem > .modal-box'),'none')
        self.assertEqual(self.page.locator('#menuLateral').evaluate('el=>getComputedStyle(el).transitionDuration'),'0s')

    def test_motion_reduced_preference_skips_animated_splash_on_fresh_visit(self):
        self.portal()
        other=self.context.new_page()
        other.emulate_media(reduced_motion='reduce')
        other.goto(safety.ORIGIN+'/index.html')
        self.assertIsNone(other.locator('#gifSplash').get_attribute('src'))
        self.assertEqual(other.locator('#splashScreenAnimacao').evaluate('el=>getComputedStyle(el).display'),'none')
        other.close()

    def test_motion_keyboard_focus_and_error_page(self):
        self.portal();self.page.evaluate('abrirModalCadastrarAluno()')
        button=self.page.locator('#btnSalvarAlunoItem')
        button.focus()
        self.assertEqual(button.evaluate('el=>getComputedStyle(el).outlineStyle'),'solid')
        self.page.goto(safety.ORIGIN+'/404.html')
        self.assertTrue(self.page.locator('.exit-link[href="/"]').is_visible())
        self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(self.page.locator('.card-inner').first.evaluate('el=>getComputedStyle(el).transitionDuration'),'0s')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(MotionTests(name) for name in loader.getTestCaseNames(MotionTests) if name.startswith('test_motion_'))

if __name__=='__main__':unittest.main(verbosity=2)
