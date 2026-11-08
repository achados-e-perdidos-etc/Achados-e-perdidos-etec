"""Comprovantes privados e impressão isolada: sem impressora ou serviço externo."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,item,codigo,confirmar
from tests.test_evolucao_browser import runtime
from tests.test_catalogo_browser import admin
from utils.comprovantes import gerar_html_comprovante,abrir_impressao_desktop
import server

ADMIN=auth('secretaria@etec.sp.gov.br',True)


def entregar(db):
    client=server.app.test_client();id=item(db);code=codigo(client,id)
    result=confirmar(client,id,code);assert result.status_code==200,result.json
    return id,result.json['comprovante_id']


def test_recibo_privado_conserva_dados_e_reversao_mesmo_apos_excluir_objeto(db):
    item_id,recibo=entregar(db);client=server.app.test_client();url=f'/api/retiradas/comprovantes/{recibo}'
    assert client.get(url).status_code==401
    assert client.get(url,headers=auth()).status_code==403
    response=client.get(url,headers=ADMIN);assert response.status_code==200,response.json
    dados=response.json['comprovante'];assert dados['item_id']==item_id and dados['tem_assinatura'] is True
    assert not {'assinatura','codigo','email_aluno'}&dados.keys()
    assert dados['data_entrega']==scalar(db,'SELECT data_entrega FROM entregues WHERE id=%s',(recibo,))
    assert 'no-store' in response.headers['Cache-Control']
    assert client.put(f'/api/itens/{item_id}/recusar',headers=ADMIN,json={'entrega_id':recibo}).status_code==200
    assert client.delete(f'/api/itens/{item_id}',headers=ADMIN).status_code==200
    dados=client.get(url,headers=ADMIN).json['comprovante'];assert dados['cancelada_em'] and dados['cancelada_por']=='secretaria@etec.sp.gov.br'
    assert client.get('/api/retiradas/comprovantes/2147483647',headers=ADMIN).status_code==404


def test_html_desktop_escapa_texto_e_nao_inventa_assinatura():
    html=gerar_html_comprovante({'item_id':7,'nome_item':'<img src=x onerror=alert(1)>','retirado_por':'Ana & João','data_entrega':'06/11/2026 10:00','cancelada_em':'2026-11-07','cancelada_por':'Secretaria'})
    assert '<img src=x' not in html and '&lt;img src=x' in html and 'Ana &amp; João' in html
    assert 'ENTREGA REVERTIDA' in html and 'não possui assinatura digitalizada' in html
    assert 'window.print()' in html and '@page{size:A4' in html


def test_desktop_arquivo_temporario_e_falha_do_navegador_limpos():
    with patch('utils.comprovantes.webbrowser.open',return_value=True) as browser:
        pasta=abrir_impressao_desktop({'item_id':7,'nome_item':'Estojo'});arquivo=Path(pasta.name)/'comprovante.html'
        assert arquivo.is_file() and arquivo.stat().st_mode&0o777==0o600
        assert browser.call_args.args[0]==arquivo.as_uri()
        pasta.cleanup();assert not arquivo.exists()
    with patch('utils.comprovantes.webbrowser.open',return_value=False):
        with pytest.raises(RuntimeError,match='navegador'):abrir_impressao_desktop({'item_id':7})


def test_historico_com_aceite_imprime_so_recibo_a4_e_revertido_identificado(runtime):
    browser,origin,db=runtime;item_id,recibo=entregar(db);context,page,errors=admin(browser,origin)
    try:
        page.evaluate("trocarAba('entregues')")
        page.get_by_role('button',name='Comprovante / Imprimir',exact=True).click()
        page.wait_for_selector('dialog[open] .comprovante-papel img')
        page.wait_for_selector('dialog[open] button:text-is("Imprimir comprovante")')
        assert 'Calculadora Casio azul' in page.locator('dialog[open] .comprovante-papel').inner_text()
        page.evaluate('''()=>{window.print=()=>{window.capturaImpressao={texto:document.getElementById('areaImpressaoComprovante').innerText,semBotoes:document.querySelectorAll('#areaImpressaoComprovante button').length,ativo:document.body.classList.contains('imprimindo-comprovante')};};}''')
        page.get_by_role('button',name='Imprimir comprovante',exact=True).click()
        page.wait_for_function('window.capturaImpressao!==undefined')
        assert page.evaluate('capturaImpressao.ativo && capturaImpressao.semBotoes===0')
        assert 'Calculadora Casio azul' in page.evaluate('capturaImpressao.texto')
        assert page.locator('#areaImpressaoComprovante').count()==0
        assert not page.evaluate('document.body.classList.contains("imprimindo-comprovante")')
        # Emulação de impressão usa a mesma folha isolada do botão e gera um PDF real.
        page.evaluate("ComprovantesEntrega.preparar(document.querySelector('dialog[open] .comprovante-papel'));document.body.classList.add('imprimindo-comprovante')")
        page.emulate_media(media='print')
        assert page.locator('.header-secretaria').is_hidden()
        assert page.locator('#areaImpressaoComprovante').is_visible()
        assert page.locator('dialog[open]').is_hidden()
        out=Path('/workspace/comprovantes-evidencias');out.mkdir(exist_ok=True)
        page.pdf(path=str(out/'comprovante-exemplo.pdf'),prefer_css_page_size=True,print_background=False)
        page.screenshot(path=str(out/'comprovante-impressao.png'),full_page=True)
        page.emulate_media(media='screen');page.evaluate('ComprovantesEntrega.limpar()');page.locator('dialog[open] .ev-close').click()
        assert server.app.test_client().put(f'/api/itens/{item_id}/recusar',headers=ADMIN,json={'entrega_id':recibo}).status_code==200
        page.evaluate('id=>ComprovantesEntrega.abrirRegistro(id)',recibo)
        page.wait_for_selector('dialog[open] .comprovante-revertido')
        assert 'ENTREGA REVERTIDA' in page.locator('.comprovante-revertido').inner_text()
        assert errors==[]
    finally:context.close()


def test_botao_do_comprovante_manual_imprime_somente_termo(runtime):
    browser,origin,db=runtime;context,page,errors=admin(browser,origin)
    try:
        page.evaluate('''()=>{document.getElementById('comprovanteDadosBox').textContent='Aluno de teste · Objeto #7: Estojo azul';document.getElementById('modalComprovante').classList.remove('hidden');window.print=()=>{window.impresso=document.getElementById('areaImpressaoComprovante').innerText;};}''')
        page.locator('#modalComprovante').get_by_role('button',name='Imprimir',exact=True).click()
        page.wait_for_function('window.impresso!==undefined')
        assert 'Estojo azul' in page.evaluate('window.impresso')
        assert 'Baixar TXT' not in page.evaluate('window.impresso')
        assert page.locator('#modalComprovante').is_visible()
        assert errors==[]
    finally:context.close()


