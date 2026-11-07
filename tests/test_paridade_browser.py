"""Ações da secretaria web exercidas com o mesmo banco/API do aplicativo."""
from pathlib import Path
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from tests.test_evolucao_browser import runtime
from tests.test_catalogo_browser import admin
from tests.test_catalogo_moderacao import inserir
import server


def test_web_filtra_sem_acentos_abre_id_etiqueta_documentos_e_png(runtime):
    browser,origin,db=runtime;id=inserir(db,nome='Óculos azul',categoria='ACESSÓRIOS');inserir(db,nome='Calculadora')
    context,page,errors=admin(browser,origin)
    try:
        page.wait_for_function('itensSec.length===2')
        page.locator('#inputBusca').fill('oculos');page.wait_for_function("document.querySelectorAll('#gridItensContainer .item-card').length===1")
        assert 'Óculos azul' in page.locator('#gridItensContainer').inner_text()
        page.locator('#secFiltroLocal').fill('patio');page.locator('#secFiltroInicio').fill('2026-11-01');page.locator('#secFiltroFim').fill('2026-11-07')
        assert page.locator('#gridItensContainer .item-card').count()==1
        page.locator('#secBuscaID').fill('ETEC-ITEM-'+str(id));page.get_by_role('button',name='Abrir por ID',exact=True).click()
        assert page.locator('#modalDetalhesItem').is_visible()
        page.get_by_role('button',name='Etiqueta individual',exact=True).click()
        page.wait_for_function("Acessibilidade.ativo?.tagName==='DIALOG'")
        page.keyboard.press('Tab');assert page.evaluate("document.querySelector('dialog[open]').contains(document.activeElement)")
        with page.expect_download() as download:page.get_by_role('button',name='Baixar etiqueta PNG',exact=True).click()
        assert download.value.suggested_filename=='etiqueta-'+str(id)+'.png'
        page.keyboard.press('Escape');page.wait_for_function("!document.querySelector('dialog[open]')")
        page.evaluate("fecharModal('modalDetalhesItem')")
        page.evaluate('abrirModalRelatorioPDF()');page.locator('#tipoRelatorioPDF').select_option('INVENTARIO')
        with page.expect_popup() as popup:page.get_by_role('button',name='Gerar / Imprimir em PDF',exact=False).click()
        report=popup.value;report.wait_for_selector('tbody tr')
        assert report.locator('tbody tr').count()==1 and 'Óculos azul' in report.locator('tbody').inner_text()
        assert report.locator('script').count()==0
        out=Path('/workspace/paridade-evidencias');out.mkdir(exist_ok=True);report.pdf(path=str(out/'relatorio-web.pdf'),prefer_css_page_size=True)
        report.close();page.evaluate('abrirModalRelatorioPDF()')
        with page.expect_download() as download:page.get_by_role('button',name='Baixar CSV deste relatório',exact=True).click()
        assert download.value.suggested_filename=='relatorio-inventario.csv'
        page.evaluate("fecharModal('modalRelatorioPDF')")
        for width in [390,1366]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(out/'secretaria-web-filtros.png'),full_page=False)
        assert errors==[]
    finally:context.close()


def test_web_mural_usa_matches_do_servidor_e_prepara_entrega(runtime):
    browser,origin,db=runtime;id=inserir(db,nome='Calculadora Casio azul',categoria='ELETRÔNICOS')
    with db() as co:
        with co.cursor() as c:c.execute("INSERT INTO mural_perdidos(nome_aluno,rm_aluno,email_aluno,categoria,descricao,data_registro,status) VALUES('Aluno','12345','a@aluno.cps.sp.gov.br','ELETRÔNICOS','Perdi calculadora Casio azul','06/11/2026','PROCURANDO')")
    context,page,errors=admin(browser,origin)
    try:
        canonical=server.app.test_client().get('/api/smart-match',headers=auth('secretaria@etec.sp.gov.br',True)).json
        page.evaluate("trocarAba('mural')")
        page.wait_for_function('PainelParidade.matches.size===1')
        page.locator('#tabelaMuralBody button').first.click()
        assert 'Calculadora Casio azul' in page.locator('#smartMatchItensContainer').inner_text()
        assert page.evaluate('[...PainelParidade.matches.values()][0][0].score')==canonical['resultados'][0]['matches'][0]['score']
        page.locator('#smartMatchItensContainer button').click()
        assert page.locator('#baixaNomeAluno').input_value()=='Aluno'
        assert page.locator('#baixaRmAluno').input_value()=='12345'
        assert scalar(db,'SELECT count(*) FROM entregues')==0
        assert errors==[]
    finally:context.close()


def test_foto_camera_web_captura_e_libera_stream_sem_dispositivo_fisico(runtime):
    browser,origin,db=runtime;context,page,errors=admin(browser,origin)
    try:
        page.evaluate('''()=>{const c=document.createElement('canvas');c.width=640;c.height=480;c.getContext('2d').fillRect(0,0,640,480);window.cameraTeste=c.captureStream(10);Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>window.cameraTeste});}''')
        page.evaluate('abrirModalCadastrar()')
        page.get_by_role('button',name='Fotografar com câmera',exact=True).click()
        page.get_by_role('button',name='Ativar câmera',exact=True).click()
        page.wait_for_function("document.querySelector('dialog[open] video').videoWidth>0")
        page.get_by_role('button',name='Usar esta foto',exact=True).click()
        page.wait_for_function('fotosBase64Upload.length===1')
        assert page.locator('#secFotosPreview img').count()==1
        assert page.evaluate("cameraTeste.getTracks().every(t=>t.readyState==='ended')")
        page.get_by_role('button',name='Remover foto 1',exact=True).click()
        assert page.evaluate('fotosBase64Upload.length')==0
        assert errors==[]
    finally:context.close()


def test_etiquetas_pdf_respeitam_quinze_por_pagina_sem_folha_so_com_cabecalho(runtime):
    from pypdf import PdfReader
    import io
    browser,origin,db=runtime
    for n in range(16):inserir(db,nome='Objeto '+str(n))
    html=server.app.test_client().get('/api/secretaria/documentos?tipo=ETIQUETAS',headers=auth('secretaria@etec.sp.gov.br',True)).json['html']
    page=browser.new_page()
    try:
        page.set_content(html);page.emulate_media(media='print');blob=page.pdf(prefer_css_page_size=True)
        pdf=PdfReader(io.BytesIO(blob));assert len(pdf.pages)==2
        assert pdf.pages[0].extract_text().count('Objeto #')==15
        assert pdf.pages[1].extract_text().count('Objeto #')==1
        out=Path('/workspace/paridade-evidencias');out.mkdir(exist_ok=True);(out/'etiquetas-duas-paginas.pdf').write_bytes(blob)
    finally:page.close()
