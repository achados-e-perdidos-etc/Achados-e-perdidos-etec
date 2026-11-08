"""Abertura limitada: nenhum GIF, falhas não bloqueiam o acesso e mídia é liberada."""
import browser_text_safety as safety
import unittest


class AberturaTests(safety.TextSafetyBrowser):
    def setUp(self):
        super().setUp();self.open()
    def nova(self,width=390,height=844):
        contexto=self.browser.new_context(viewport={'width':width,'height':height},service_workers='block')
        contexto.route('**/*',self.route);pagina=contexto.new_page();pagina.set_default_timeout(6000)
        return contexto,pagina

    def test_video_correto_por_tela_pode_ser_pulado_e_nao_reabre(self):
        for width,height,nome in [(390,844,'abertura-celular.mp4'),(1366,900,'abertura-computador.mp4')]:
            contexto,pagina=self.nova(width,height);urls=[];pagina.on('request',lambda r:urls.append(r.url))
            try:
                pagina.goto(safety.ORIGIN,wait_until='domcontentloaded')
                pagina.locator('#pularAbertura').click()
                self.assertFalse(pagina.locator('#splashScreenAnimacao').is_visible())
                self.assertTrue(pagina.locator('#loginAlunoScreen').is_visible())
                self.assertIsNone(pagina.locator('#videoAbertura').get_attribute('src'))
                self.assertTrue(any(u.endswith(nome) for u in urls),urls)
                self.assertFalse(any('.GIF' in u or '.gif' in u for u in urls))
                antes=len([u for u in urls if u.endswith('.mp4')]);pagina.reload()
                self.assertFalse(pagina.locator('#splashScreenAnimacao').is_visible())
                self.assertEqual(len([u for u in urls if u.endswith('.mp4')]),antes)
            finally:contexto.close()

    def test_video_lento_tem_limite_e_falha_nao_impede_login(self):
        for erro in [False,True]:
            contexto,pagina=self.nova()
            if erro:contexto.route('**/*.mp4',lambda route:route.abort())
            else:pagina.add_init_script("Object.defineProperty(HTMLMediaElement.prototype,'src',{set(v){this.dataset.solicitado=v},get(){return ''}});HTMLMediaElement.prototype.play=()=>new Promise(()=>{})")
            try:
                pagina.goto(safety.ORIGIN,wait_until='domcontentloaded')
                pagina.wait_for_function("document.getElementById('splashScreenAnimacao').hidden",timeout=5000)
                self.assertTrue(pagina.locator('#loginAlunoScreen').is_visible())
                self.assertTrue(pagina.locator('#videoAbertura').evaluate('v=>v.paused'))
            finally:contexto.close()

    def test_economia_de_dados_pula_video_e_escape_libera_midia(self):
        contexto,pagina=self.nova();urls=[];pagina.on('request',lambda r:urls.append(r.url))
        pagina.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true}})")
        try:
            pagina.goto(safety.ORIGIN);self.assertFalse(any(u.endswith('.mp4') for u in urls))
            self.assertFalse(pagina.locator('#splashScreenAnimacao').is_visible())
        finally:contexto.close()
        contexto,pagina=self.nova()
        try:
            pagina.goto(safety.ORIGIN,wait_until='domcontentloaded')
            pagina.locator('#pularAbertura').focus();pagina.keyboard.press('Escape')
            self.assertFalse(pagina.locator('#splashScreenAnimacao').is_visible())
            self.assertIsNone(pagina.locator('#videoAbertura').get_attribute('src'))
        finally:contexto.close()


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(AberturaTests(nome) for nome in loader.getTestCaseNames(AberturaTests) if nome in AberturaTests.__dict__)
