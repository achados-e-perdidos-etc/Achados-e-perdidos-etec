"""Fotos reais no navegador e respostas de envio simuladas, sem Cloudinary real."""
import base64
import struct
import unittest
import zlib
import browser_text_safety as safety


def png():
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',4,4,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\xff\x00\x00\xff'*4)*4))+chunk(b'IEND',b'')


class UploadTests(safety.TextSafetyBrowser):
    def portal(self):
        self.open();self.page.add_style_tag(content='.hidden{display:none!important}')
        self.page.evaluate("abrirModalCadastrarAluno()")

    def panel(self):
        self.open(admin=True)
        self.page.evaluate("()=>{document.getElementById('modalFormItem').classList.remove('hidden');analisarFotoSecretariaComIA=async()=>{};}")

    def photo(self, admin=False, broken=False):
        self.page.locator('#formItemFotosInput' if admin else '#alunoItemFoto').set_input_files({
            'name':'foto.png','mimeType':'image/png','buffer':b'invalido' if broken else png()})
        self.page.wait_for_function("id=>['prontas','erro'].includes(document.getElementById(id).dataset.estado)",arg='estadoEnvioSecretaria' if admin else 'statusCompressaoFotos')

    def saving(self, admin=False):
        self.page.evaluate('''admin=>{
          (admin ? UploadSecretaria : UploadAluno).enviarTodas=async fotos=>fotos;
          window._posts=0;window.fetch=async(url,opts)=>{
            if(String(url).endsWith('/api/itens/duplicados'))return {ok:true,json:async()=>({success:true,duplicados:[]})};
            if(opts?.method==='POST'||opts?.method==='PUT'){
              window._posts++;return new Promise(resolve=>window._finish=resolve);
            }return {ok:true,json:async()=>[]};
          };
          if(admin){tokenSecretaria='teste';document.getElementById('formItemId').value='';}
          window._pending=(admin?salvarItemForm:enviarCadastroAluno)({preventDefault(){},target:{reset(){}}});
        }''',admin)

    def finish(self, success=True):
        self.page.evaluate("success=>window._finish({ok:success,status:success?200:502,json:async()=>({success,message:'Falha simulada'})})",success)
        self.page.evaluate('window._pending')

    def test_upload_portal_realtime_and_duplicate_guard(self):
        self.portal();self.photo()
        self.assertEqual(self.page.evaluate('fotosAlunoSelecionadas.length'),1)
        self.assertIn('ao salvar',self.page.locator('#statusCompressaoFotos').text_content())
        self.saving()
        self.assertEqual(self.page.locator('#statusCompressaoFotos').get_attribute('data-estado'),'enviando')
        self.assertEqual(self.page.locator('#statusCompressaoFotos').get_attribute('aria-busy'),'true')
        self.assertTrue(self.page.locator('#btnSalvarAlunoItem').is_disabled())
        self.page.evaluate('enviarCadastroAluno({preventDefault(){}})')
        self.assertEqual(self.page.evaluate('window._posts'),1)
        self.finish()
        self.assertEqual(self.page.locator('#statusCompressaoFotos').get_attribute('data-estado'),'sucesso')
        self.assertFalse(self.page.locator('#btnSalvarAlunoItem').is_disabled())
        self.assertIn('Fotos enviadas',self.page.locator('#toastContainer').text_content())

    def test_upload_failure_keeps_photos_for_retry(self):
        self.portal();self.photo();before=self.page.evaluate('fotosAlunoSelecionadas.slice()')
        self.saving();self.finish(False)
        self.assertEqual(self.page.locator('#statusCompressaoFotos').get_attribute('data-estado'),'erro')
        self.assertEqual(self.page.evaluate('fotosAlunoSelecionadas'),before)
        self.assertFalse(self.page.locator('#alunoItemFoto').is_disabled())
        self.assertFalse(self.page.locator('#modalCadastrarAluno').evaluate("el=>el.classList.contains('hidden')"))

    def test_upload_preparation_blocks_save_and_old_completion_is_ignored(self):
        self.portal()
        self.page.evaluate("()=>{comprimirImagem=()=>new Promise(resolve=>window._prepared=resolve);}")
        self.page.locator('#alunoItemFoto').set_input_files({'name':'foto.png','mimeType':'image/png','buffer':png()})
        self.assertTrue(self.page.locator('#btnSalvarAlunoItem').is_disabled())
        self.page.evaluate("enviarCadastroAluno({preventDefault(){}})")
        self.assertFalse(self.page.evaluate('envioCadastroAluno'))
        self.page.evaluate('abrirModalCadastrarAluno()')
        self.page.evaluate("window._prepared('data:image/jpeg;base64,YQ==')")
        self.page.wait_for_function('!preparandoFotosAluno')
        self.assertEqual(self.page.evaluate('fotosAlunoSelecionadas.length'),0)

    def test_upload_bad_file_no_false_green_and_reduced_motion(self):
        self.portal();self.page.emulate_media(reduced_motion='reduce');self.photo(broken=True)
        self.assertEqual(self.page.locator('#statusCompressaoFotos').get_attribute('data-estado'),'erro')
        self.assertEqual(self.page.evaluate('fotosAlunoSelecionadas.length'),0)
        self.assertFalse(self.page.locator('#btnSalvarAlunoItem').is_disabled())
        self.assertEqual(self.page.locator('.estado-fotos-icone').evaluate('el=>getComputedStyle(el).animationName'),'none')

    def test_upload_panel_success_and_failure(self):
        self.panel();self.photo(admin=True)
        self.assertEqual(self.page.evaluate('fotosBase64Upload.length'),1)
        self.saving(admin=True)
        self.page.evaluate('salvarItemForm({preventDefault(){}})')
        self.assertEqual(self.page.evaluate('window._posts'),1)
        self.finish(False)
        self.assertEqual(self.page.locator('#estadoEnvioSecretaria').get_attribute('data-estado'),'erro')
        self.assertEqual(self.page.evaluate('fotosBase64Upload.length'),1)
        self.saving(admin=True);self.finish()
        self.assertEqual(self.page.locator('#estadoEnvioSecretaria').get_attribute('data-estado'),'sucesso')
        self.assertIn('✓ Fotos enviadas',self.page.locator('#toast').text_content())

    def test_upload_panel_invalid_replacement_preserves_existing_photos(self):
        self.panel()
        self.page.evaluate("fotosBase64Upload=['https://images.example.org/existente.jpg']")
        self.photo(admin=True,broken=True)
        self.assertEqual(self.page.evaluate('fotosBase64Upload'),['https://images.example.org/existente.jpg'])
        self.assertEqual(self.page.locator('#estadoEnvioSecretaria').get_attribute('data-estado'),'erro')
        self.assertFalse(self.page.locator('#btnSalvarItem').is_disabled())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(UploadTests(name) for name in loader.getTestCaseNames(UploadTests) if name.startswith('test_upload_'))

if __name__=='__main__':unittest.main(verbosity=2)
