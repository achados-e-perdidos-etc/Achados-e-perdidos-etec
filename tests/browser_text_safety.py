"""Regressão no Chromium com páginas reais e rede inteiramente simulada.

Opcional: pip install playwright; playwright install chromium
Execute: python tests/browser_text_safety.py
CHROMIUM_PATH permite usar um Chromium já instalado, sem baixar outro.
Não usa credenciais, banco ou serviços externos.
"""
import mimetypes
import os
from pathlib import Path
import unittest
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://etec-teste.invalid"
PAYLOAD = '''João D'Ávila "&" <img src=x onerror="window.__xss=1"> <svg onload="window.__xss=2"></svg> ');window.__xss=3;//'''


class TextSafetyBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        options = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if os.environ.get("CHROMIUM_PATH"):
            options["executable_path"] = os.environ["CHROMIUM_PATH"]
        cls.browser = cls.playwright.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(service_workers="block")
        self.context.route("**/*", self.route)
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.add_init_script("sessionStorage.setItem('splash_ja_exibido','true'); window.__xss=0;")

    def route(self, route):
        url = urlparse(route.request.url)
        file = ROOT / (url.path.lstrip("/") or "index.html")
        if url.netloc == "etec-teste.invalid" and file.is_file() and ROOT in file.resolve().parents:
            route.fulfill(body=file.read_bytes(), content_type=mimetypes.guess_type(file)[0] or "application/octet-stream")
        elif "/api/" in url.path:
            route.fulfill(body="[]", content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})
        else:
            route.fulfill(status=200, body="", content_type="text/javascript" if route.request.resource_type == "script" else "text/plain")

    def open(self, admin=False):
        self.page.goto(ORIGIN + ("/controle_etec_7788.html" if admin else "/index.html"))
        self.page.evaluate("window.fetch=async()=>({ok:true,json:async()=>window._fixture || []});")

    def fixture(self, rows):
        self.page.evaluate("rows=>window._fixture=rows", rows)

    def assert_safe(self, selector):
        self.assertEqual(self.page.locator(selector).locator("svg,script,iframe,object,[onerror],[onload]").count(), 0)
        self.assertEqual(self.page.evaluate("window.__xss"), 0)

    def tearDown(self):
        try:
            self.assertEqual(self.page.evaluate("window.__xss"), 0)
            self.assertEqual(self.errors, [])
        finally:
            self.context.close()

    def test_catalog_and_details_preserve_text_and_click_argument(self):
        self.open()
        item = dict(id=8, nome=PAYLOAD, categoria=PAYLOAD, txt_descricao=PAYLOAD,
                    txt_local=PAYLOAD, txt_data="06/11/2026", status="DISPONÍVEL", fotos=["javascript:window.__xss=4"])
        self.page.evaluate("item=>{todosItens=[item]; renderizarItens();}", item)
        self.assertEqual(self.page.locator("#itemsGrid h4").text_content(), PAYLOAD)
        self.assert_safe("#itemsGrid")
        self.assertEqual(self.page.locator("#itemsGrid img").get_attribute("src"), "")
        self.page.locator("#itemsGrid .interactive-card").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("itemSelecionado"), item)
        self.assertEqual(self.page.locator("#detailTitle").text_content(), PAYLOAD)
        self.assert_safe("#carouselContainer")
        self.page.evaluate("abrirZoomImagem('javascript:window.__xss=5')")
        self.assertFalse(self.page.locator("#modalZoomImagem").evaluate("el=>el.classList.contains('ativo')"))

    def test_categories_preserve_quotes_in_options_and_handlers(self):
        self.open()
        self.fixture([dict(nome=PAYLOAD)])
        self.page.evaluate("carregarCategoriasDinamicamente()")
        self.assertEqual(self.page.locator("#muralCategoria").input_value(), PAYLOAD)
        self.assertEqual(self.page.locator("#dynamicChipsList button").text_content().strip(), PAYLOAD)
        self.page.evaluate("selecionarFiltroCategoria=(...args)=>window._clicked=args")
        self.page.locator("#dynamicChipsList button").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("window._clicked"), [PAYLOAD, PAYLOAD])
        self.assert_safe("#dynamicChipsList")

    def test_public_mural_and_toast_display_literal_text(self):
        self.open()
        self.fixture([dict(categoria=PAYLOAD, descricao=PAYLOAD, nome_aluno=PAYLOAD, data_registro=PAYLOAD)])
        self.page.evaluate("carregarMuralPublico()")
        self.assertIn(PAYLOAD, self.page.locator("#listaMuralPublico").text_content())
        self.assert_safe("#listaMuralPublico")
        self.page.evaluate("text=>mostrarToast(text)", PAYLOAD)
        self.assertEqual(self.page.locator("#toastContainer p").last.text_content(), PAYLOAD)
        self.assert_safe("#toastContainer")

    def test_portal_chat_both_senders_and_private_items(self):
        self.open()
        self.fixture([dict(remetente=role, mensagem=PAYLOAD) for role in ["ALUNO", "SECRETARIA"]])
        self.page.evaluate("alunoSessao={rm:'12345'}; ultimaQtdMensagens=0; atualizarMensagensChat()")
        self.assertEqual(self.page.locator("#chatMensagens").text_content().count(PAYLOAD), 2)
        self.assert_safe("#chatMensagens")
        self.fixture([dict(id=9, nome=PAYLOAD, status="SOLICITADO", descricao=PAYLOAD,
                           categoria=PAYLOAD, data_registro=PAYLOAD)])
        self.page.evaluate("abrirPainelMeusItens()")
        self.assertIn(PAYLOAD, self.page.locator("#listaMinhasSolicitacoes").text_content())
        self.assert_safe("#listaMinhasSolicitacoes")
        self.assert_safe("#listaMeusRelatosMural")

    def test_admin_chat_and_conversation_selection(self):
        self.open(admin=True)
        self.page.evaluate("p=>{listaConversasCache=[{rm_aluno:p,nome_aluno:p,ultima_mensagem:p}]; renderizarListaConversasChat();}", PAYLOAD)
        self.assertIn(PAYLOAD, self.page.locator("#chatListaConversasContainer").text_content())
        self.assert_safe("#chatListaConversasContainer")
        self.page.evaluate("selecionarConversaAluno=(...args)=>window._clicked=args")
        self.page.locator("#chatListaConversasContainer .card-conversa-aluno").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("window._clicked"), [PAYLOAD, PAYLOAD, None])
        self.fixture([dict(remetente=role, mensagem=PAYLOAD, nome_aluno=PAYLOAD, data_envio=PAYLOAD)
                      for role in ["ALUNO", "SECRETARIA"]])
        self.page.evaluate("chatRmAtivo='12345';carregarMensagensConversa('12345')")
        self.assertEqual(self.page.locator("#chatMensagensContainer .msg-balao").count(), 2)
        self.assertIn(PAYLOAD, self.page.locator("#chatMensagensContainer").text_content())
        self.assert_safe("#chatMensagensContainer")

    def test_admin_details_categories_and_image_open(self):
        self.open(admin=True)
        self.page.evaluate("p=>{itensSec=[{id:7,nome:p,categoria:p,txt_descricao:p,txt_local:p,txt_data:p,solicitado_por:p,rm_aluno:p,fotos:['javascript:window.__xss=6']}]; abrirDetalhesItem(7); categoriasSec=[{nome:p}]; renderizarCategorias();}", PAYLOAD)
        self.assertIn(PAYLOAD, self.page.locator("#detalhesInfoCard").text_content())
        self.assert_safe("#detalhesInfoCard")
        self.assertEqual(self.page.locator("#detalhesGaleriaFotos img").get_attribute("src"), "")
        self.page.evaluate("()=>{window.open=(...args)=>window._opened=args;}")
        self.page.locator("#detalhesGaleriaFotos img").evaluate("el=>el.click()")
        self.assertIsNone(self.page.evaluate("window._opened"))
        self.page.evaluate("abrirImagemSegura('https://images.example.org/foto.png')")
        self.assertEqual(self.page.evaluate("window._opened"), ["https://images.example.org/foto.png", "_blank", "noopener,noreferrer"])
        self.page.evaluate("removerCategoria=nome=>window._category=nome")
        self.page.locator("#tabelaCategoriasBody button").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("window._category"), PAYLOAD)
        self.assert_safe("#tabelaCategoriasBody")

    def test_formatted_dialog_only_keeps_basic_tags_without_attributes(self):
        self.open(admin=True)
        message = '<strong onclick="window.__xss=7">Atenção &amp; ação</strong><br>' + PAYLOAD + '<script>window.__xss=8</script><iframe srcdoc="x"></iframe>'
        self.page.evaluate("mensagem=>{abrirAlertaModal({mensagem}); abrirConfirmacaoModal({mensagem});}", message)
        for selector in ["#alertaMensagem", "#confirmMensagem"]:
            self.assert_safe(selector)
            self.assertEqual(self.page.locator(selector + " strong").text_content(), "Atenção & ação")
            self.assertEqual(self.page.locator(selector + " strong").evaluate("el=>el.attributes.length"), 0)
            self.assertEqual(self.page.locator(selector + " [onclick]").count(), 0)

    def test_match_actions_preserve_original_objects_and_names(self):
        self.open()
        item = dict(id=7, nome=PAYLOAD, txt_descricao=PAYLOAD, categoria=PAYLOAD, status="DISPONÍVEL")
        self.page.evaluate("item=>exibirMatchesImediatos([item])", item)
        self.assert_safe("#matchItensLista")
        self.page.evaluate("()=>{abrirDetalhes=item=>window._selected=item;}")
        self.page.locator("#matchItensLista button").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("window._selected"), item)
        self.open(admin=True)
        self.page.evaluate("p=>{itensSec=[{id:7,nome:p,status:'DISPONÍVEL'}]; listaMuralGlobal=[{id:3,nome_aluno:p,rm_aluno:p,descricao:p,categoria:p}]; calcularSmartMatchCliente=()=>({score:80,motivos:[p]}); abrirModalComparacaoMatch(3);}", PAYLOAD)
        self.assert_safe("#smartMatchRelatoBox")
        self.assert_safe("#smartMatchItensContainer")
        self.assertIn(PAYLOAD, self.page.locator("#smartMatchItensContainer").text_content())
        self.page.evaluate("()=>{prepararBaixaPorMatch=(...args)=>window._match=args;}")
        self.page.locator("#smartMatchItensContainer button").evaluate("el=>el.click()")
        self.assertEqual(self.page.evaluate("window._match"), [7, PAYLOAD, PAYLOAD])

    def test_reports_escape_fields_in_print_document(self):
        self.open(admin=True)
        self.page.evaluate("p=>{itensSec=[{id:7,nome:p,categoria:p,txt_local:p,txt_data:p,status:'DISPONÍVEL'}]; window.open=()=>({document:{open(){},write(s){window._printed=s},close(){}}});}", PAYLOAD)
        self.page.evaluate("document.getElementById('tipoRelatorioPDF').value='INVENTARIO'")
        self.page.evaluate("gerarRelatorioPDFOficial()")
        self.page.evaluate("()=>{const frame=document.createElement('iframe'); frame.id='reportTest'; frame.srcdoc=window._printed; document.body.append(frame)}")
        frame = self.page.frame_locator("#reportTest")
        self.assertEqual(frame.locator("tbody img,tbody svg,tbody script").count(), 0)
        self.assertIn(PAYLOAD, frame.locator("tbody").text_content())
        # O relatório de entregas usa campos de aluno e responsável distintos.
        self.fixture([dict(item_id=7, nome_item=PAYLOAD, retirado_por=PAYLOAD, rm_retirante=PAYLOAD,
                           turma_curso=PAYLOAD, data_entrega=PAYLOAD, funcionario_responsavel=PAYLOAD)])
        self.page.evaluate("document.getElementById('tipoRelatorioPDF').value='ENTREGAS'")
        self.page.evaluate("gerarRelatorioPDFOficial()")
        self.page.evaluate("document.getElementById('reportTest').srcdoc=window._printed")
        self.assertEqual(frame.locator("tbody img,tbody svg,tbody script").count(), 0)
        self.assertEqual(frame.locator("tbody").text_content().count(PAYLOAD), 6)

    def test_image_protocols_and_context_encoding(self):
        self.open()
        blocked = ["", "  ", None, "javascript:window.__xss=9", "data:text/html,<script>x</script>",
                   "data:image/svg+xml,<svg onload=alert(1)>", "file:///etc/passwd", "vbscript:msgbox(1)"]
        self.assertEqual(self.page.evaluate("urls=>urls.map(urlImagemSegura)", blocked), [""] * len(blocked))
        allowed = ["https://images.example.org/a.png", "data:image/png;base64,iVBORw0KGgo="]
        self.assertEqual(self.page.evaluate("urls=>urls.map(urlImagemSegura)", allowed), allowed)
        self.assertEqual(self.page.evaluate("urlImagemSegura('/foto.jpg')"), ORIGIN + "/foto.jpg")
        for value in [PAYLOAD, "&lt;img&gt;", "áéî中😀", "linha\nseguinte", None, 7]:
            result = self.page.evaluate("v=>{const d=document.createElement('div'); d.innerHTML=textoHTML(v); return d.textContent}", value)
            self.assertEqual(result, "" if value is None else str(value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
