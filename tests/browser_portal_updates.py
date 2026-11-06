"""Interface real, APIs simuladas: histórico, rascunhos e teclado."""
import unittest
import browser_text_safety as safety

class PortalUpdates(safety.TextSafetyBrowser):
    def prepare(self):
        self.open(); self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate('''()=>{
            document.getElementById('loginAlunoScreen').classList.add('hidden');
            document.getElementById('loadingOverlay').style.display='none';
            SessaoPortal.salvar('teste',{nome:'Ana',email:'ana@aluno.cps.sp.gov.br',rm:'12345'});
            alunoSessao=SessaoPortal.dados();
        }''')

    def test_notification_center_handles_content_and_failure(self):
        self.prepare()
        self.page.evaluate('''()=>{window._requests=[];window.fetch=async(url,opts)=>{
            window._requests.push([url,opts]);return {ok:true,json:async()=>({success:true,nao_lidas:1,tem_mais:false,
            notificacoes:[{id:1,titulo:'<img onerror=alert(1)>',corpo:'Mensagem privada',evento:'chat',lida:false,criada_em:'2026-11-06T10:00:00Z'}]})};};}''')
        self.page.evaluate('CentralAvisos.abrir()');self.page.wait_for_function('CentralAvisos.itens.length===1')
        self.assertEqual(self.page.locator('#listaAvisos img').count(),0)
        self.assertIn('<img',self.page.locator('#listaAvisos').text_content())
        self.assertFalse(self.page.locator('#badgeAvisos').get_attribute('hidden'))
        self.assertIn('Bearer teste',self.page.evaluate('window._requests[0][1].headers.Authorization'))
        self.page.evaluate("window.fetch=async()=>{throw Error('offline')};CentralAvisos.carregar()")
        self.page.wait_for_function("document.getElementById('statusAvisos').textContent.includes('Não foi possível')")
        self.assertIn('Mensagem privada',self.page.locator('#listaAvisos').text_content())

    def test_tracking_preserves_literal_names_and_retry(self):
        self.prepare()
        self.page.evaluate("window.fetch=async()=>({ok:true,json:async()=>({success:true,cadastros:[{id:1,nome:'<img src=x>',categoria:'OUTROS',situacao:'RECUSADO',enviado_em:'2026-11-06T10:00:00Z'}],tem_mais:false})})")
        self.page.evaluate('MeusCadastros.carregar()')
        self.page.wait_for_function('MeusCadastros.itens.length===1')
        self.assertIn('Cadastro recusado',self.page.locator('#listaMeusCadastros').text_content())
        self.assertEqual(self.page.locator('#listaMeusCadastros img').count(),0)
        self.page.evaluate("window.fetch=async()=>({ok:false,json:async()=>({success:false})}); MeusCadastros.carregar()")
        self.page.wait_for_function("document.getElementById('statusMeusCadastros').textContent.includes('Não foi possível')")

    def test_draft_survives_reload_and_is_scoped_without_photos(self):
        self.prepare(); self.page.evaluate('abrirModalCadastrarAluno()')
        self.page.locator('#alunoItemNome').fill('Mochila verde')
        self.page.locator('#alunoItemDesc').fill('Encontrada na biblioteca')
        self.page.evaluate("fotosAlunoSelecionadas=['data:image/jpeg;base64,nunca-guardar'];Rascunhos.salvar('encontrado')")
        texto=self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))")
        self.assertNotIn('base64',texto)
        self.page.reload();self.page.evaluate('abrirModalCadastrarAluno()')
        self.assertEqual(self.page.locator('#alunoItemNome').input_value(),'Mochila verde')
        self.page.evaluate("SessaoPortal.salvar('outra',{nome:'Outra',email:'outra@aluno.cps.sp.gov.br',rm:'12345'})")
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))"))
        self.assertEqual(self.page.evaluate("Object.keys(sessionStorage).filter(k=>k.startsWith(Rascunhos.prefixo)).length"),0)

    def test_draft_only_clears_after_success(self):
        self.prepare();self.page.evaluate('abrirModalCadastrarAluno()')
        self.page.locator('#alunoItemNome').fill('Caderno')
        self.page.locator('#alunoItemDesc').fill('Caderno vermelho')
        self.page.evaluate("window.fetch=async()=>({ok:false,json:async()=>({success:false})})")
        self.page.evaluate("enviarCadastroAluno({preventDefault(){},target:document.getElementById('alunoItemNome').closest('form')})")
        self.assertIsNotNone(self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))"))
        self.page.evaluate("window.fetch=async()=>({ok:true,json:async()=>({success:true})})")
        self.page.evaluate("enviarCadastroAluno({preventDefault(){},target:document.getElementById('alunoItemNome').closest('form')})")
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))"))

    def test_admin_draft_does_not_overwrite_edit(self):
        self.open(admin=True);self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate("sessionStorage.setItem('secretaria_token','x.'+btoa(JSON.stringify({email:'sec@etec.sp.gov.br'}))+'.x');document.getElementById('loginScreen').classList.add('hidden');abrirModalCadastrar()")
        self.page.locator('#formItemNome').fill('Objeto em rascunho')
        self.page.evaluate("document.getElementById('formItemId').value='55';document.getElementById('formItemNome').value='Item existente';Rascunhos.restaurar('secretaria')")
        self.assertEqual(self.page.locator('#formItemNome').input_value(),'Item existente')
        self.page.evaluate("document.getElementById('formItemId').value='';abrirModalCadastrar()")
        self.assertEqual(self.page.locator('#formItemNome').input_value(),'Objeto em rascunho')


    def test_keyboard_focus_is_trapped_and_returns_to_opener(self):
        self.prepare()
        self.page.wait_for_function('Acessibilidade.ativo===null')
        self.page.evaluate("window.fetch=async()=>({ok:true,json:async()=>({success:true,notificacoes:[],nao_lidas:0,tem_mais:false})})")
        self.page.locator('#btnCentralAvisos').click()
        self.page.wait_for_function("Acessibilidade.ativo?.id==='centralAvisos'")
        self.assertTrue(self.page.evaluate("document.getElementById('centralAvisos').contains(document.activeElement)"))
        self.assertTrue(self.page.locator('main').evaluate('el=>el.inert'))
        for _ in range(9):
            self.page.keyboard.press('Tab')
            self.assertTrue(self.page.evaluate("document.getElementById('centralAvisos').contains(document.activeElement)"))
        self.page.keyboard.press('Escape')
        self.page.wait_for_function('Acessibilidade.ativo===null')
        self.assertEqual(self.page.evaluate('document.activeElement.id'),'btnCentralAvisos')
        self.assertFalse(self.page.locator('main').evaluate('el=>el.inert'))

    def test_item_card_is_operable_by_keyboard_and_fields_have_labels(self):
        self.prepare()
        self.page.evaluate("todosItens=[{id:1,nome:'Estojo',txt_descricao:'Estojo preto',categoria:'OUTROS',txt_local:'Sala',txt_data:'06/11/2026',status:'DISPONÍVEL',fotos:[]}];renderizarItens()")
        self.page.wait_for_function("document.querySelector('.interactive-card')?.getAttribute('role')==='button'")
        card=self.page.locator('.interactive-card');card.focus();self.page.keyboard.press('Enter')
        self.assertEqual(self.page.locator('#detailTitle').text_content(),'Estojo')
        ids=['cadNome','cadRM','cadSenha','chatInputTexto','muralCategoria','alunoItemFoto']
        for id in ids:
            self.assertGreater(self.page.locator('label[for="'+id+'"]').count(),0)


    def test_admin_drawer_is_skipped_when_closed_and_escape_restores_focus(self):
        self.open(admin=True)
        self.page.evaluate("document.getElementById('loginScreen').classList.add('hidden');document.getElementById('btnHamburger').focus()")
        self.page.wait_for_function('Acessibilidade.ativo===null')
        self.assertTrue(self.page.locator('#menuLateral').evaluate('el=>el.inert'))
        self.page.locator('#btnHamburger').click()
        self.page.wait_for_function("Acessibilidade.ativo?.id==='menuLateral'")
        self.assertFalse(self.page.locator('#menuLateral').evaluate('el=>el.inert'))
        self.page.keyboard.press('Escape')
        self.page.wait_for_function('Acessibilidade.ativo===null')
        self.assertEqual(self.page.evaluate('document.activeElement.id'),'btnHamburger')
        self.assertTrue(self.page.locator('#menuLateral').evaluate('el=>el.inert'))

    def test_expired_draft_is_removed_and_user_can_discard(self):
        self.prepare();self.page.evaluate('abrirModalCadastrarAluno()')
        self.page.locator('#alunoItemNome').fill('Estojo')
        self.page.evaluate("sessionStorage.setItem(Rascunhos.chave('encontrado'),JSON.stringify({salvo:Date.now()-Rascunhos.ttl-1,campos:{alunoItemNome:'Antigo'}}));Rascunhos.restaurar('encontrado')")
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))"))
        self.page.locator('#alunoItemDesc').fill('Texto a descartar')
        self.page.once('dialog',lambda dialog:dialog.accept())
        self.page.locator('#modalCadastrarAluno .rascunho-controles button').click()
        self.assertEqual(self.page.locator('#alunoItemDesc').input_value(),'')
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem(Rascunhos.chave('encontrado'))"))


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(PortalUpdates(name) for name in loader.getTestCaseNames(PortalUpdates) if name not in loader.getTestCaseNames(safety.TextSafetyBrowser))
if __name__=='__main__':unittest.main(verbosity=2)
