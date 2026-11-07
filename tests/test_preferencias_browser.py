"""Escolha de tema, buscas e atalhos com API, PostgreSQL e Chromium reais."""
import json
from pathlib import Path
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from tests.test_evolucao_browser import runtime,portal
from tests.test_catalogo_browser import admin
from tests.test_catalogo_moderacao import inserir

OUT=Path('/workspace/preferencias-evidencias')


def test_tema_so_segue_sistema_depois_de_escolha_e_muda_em_tempo_real(runtime):
    browser,origin,db=runtime
    context=browser.new_context(viewport={'width':390,'height':844},color_scheme='light',service_workers='block')
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true")')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.emulate_media(reduced_motion='reduce',color_scheme='light')
    try:
        page.goto(origin+'/');page.wait_for_selector('#loginAlunoScreen:not(.hidden)')
        assert page.locator('html').get_attribute('data-tema')=='escuro'
        assert page.locator('#loginAuthCard .tema-pergunta').is_visible()
        page.locator('#loginAuthCard').get_by_role('button',name='Sim, usar o sistema',exact=True).click()
        assert page.locator('html').get_attribute('data-tema')=='claro'
        page.emulate_media(color_scheme='dark');page.wait_for_function("document.documentElement.dataset.tema==='escuro'")
        page.locator('#loginAuthCard').get_by_role('button',name='Escolher aparência do site').click()
        page.locator('#aparenciaDialog').get_by_role('button',name='Claro',exact=True).click()
        page.get_by_role('button',name='Concluir',exact=True).click()
        page.emulate_media(color_scheme='dark');assert page.locator('html').get_attribute('data-tema')=='claro'
        page.reload();page.wait_for_selector('#loginAlunoScreen:not(.hidden)')
        assert page.locator('html').get_attribute('data-tema')=='claro'
        assert page.locator('.tema-pergunta').count()==0
        assert page.locator('#loginAuthCard').evaluate("n=>getComputedStyle(n).backgroundColor")=='rgb(255, 255, 255)'
        assert page.locator('#loginSenhaAluno').evaluate("n=>getComputedStyle(n).color")=='rgb(25, 35, 52)'
        assert page.locator('#btnAcessoLogin').evaluate("n=>getComputedStyle(n).color")=='rgb(255, 255, 255)'
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'login-claro.png'))
        assert not errors
    finally:context.close()


def test_preferencias_storage_bloqueado_limite_remocao_e_limpeza(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        page.wait_for_function('CatalogoPortal.ativo && !CatalogoPortal.ocupado')
        page.locator('#preferenciasListas summary').click()
        # Sem filtro, a interface explica o que falta em vez de criar uma busca vazia.
        page.get_by_role('button',name='Salvar busca atual',exact=True).click()
        assert 'Escolha uma palavra' in page.locator('#preferenciasStatus').inner_text()
        page.locator('#searchInput').fill('Estojo');page.wait_for_function('!CatalogoPortal.ocupado')
        page.get_by_role('button',name='Salvar busca atual',exact=True).click()
        page.get_by_role('button',name='Salvar busca atual',exact=True).click()
        assert page.locator('.busca-salva').count()==1 and 'já está salva' in page.locator('#preferenciasStatus').inner_text()
        page.evaluate("PreferenciasUI.dados.buscas=Array.from({length:10},(_,i)=>({q:'Busca '+i,status:'TODOS',categoria:'TODOS'}));PreferenciasUI.renderizarBuscas()")
        page.get_by_role('button',name='Salvar busca atual',exact=True).click()
        assert '10 buscas' in page.locator('#preferenciasStatus').inner_text()
        page.locator('.busca-salva').first.get_by_role('button',name='Remover busca Busca 0',exact=True).click()
        assert page.locator('.busca-salva').count()==9
        page.get_by_role('button',name='Limpar preferências desta conta',exact=True).click()
        assert page.locator('.busca-salva').count()==0 and page.locator('#searchInput').input_value()==''
        page.evaluate("() => {Storage.prototype.setItem=function(){throw new DOMException('Bloqueado','QuotaExceededError')}}")
        page.get_by_role('button',name='Lista compacta',exact=True).click()
        assert 'bloqueou o salvamento' in page.locator('#preferenciasStatus').inner_text()
        assert 'preferencia-lista' in page.locator('#itemsGrid').get_attribute('class')
        page.evaluate("TemaUI.abrir()")
        page.locator('#aparenciaDialog').get_by_role('button',name='Claro',exact=True).click()
        assert 'bloqueou o salvamento' in page.locator('#aparenciaDialog [role=status]').inner_text()
        assert page.locator('html').get_attribute('data-tema')=='claro'
        assert not errors
    finally:context.close()


def test_buscas_salvas_filtros_visual_e_isolamento_de_conta(runtime):
    browser,origin,db=runtime;inserir(db,nome='Garrafa térmica azul',local='Pátio');inserir(db,nome='Caderno')
    context,page,errors=portal(browser,origin)
    try:
        page.wait_for_function('CatalogoPortal.ativo && !CatalogoPortal.ocupado')
        page.locator('main .tema-pergunta').get_by_role('button',name='Prefiro claro',exact=True).click()
        page.locator('#searchInput').fill('garrafa azul');page.locator('.catalogo-filtros summary').click();page.locator('#catalogoLocal').fill('patio')
        page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===1')
        page.locator('#preferenciasListas summary').click();page.get_by_role('button',name='Salvar busca atual',exact=True).click()
        assert page.locator('.busca-salva').count()==1
        page.get_by_role('button',name='Lista compacta',exact=True).click();page.reload()
        page.wait_for_function('CatalogoPortal.ativo && !CatalogoPortal.ocupado')
        assert page.locator('#searchInput').input_value()=='garrafa azul'
        assert page.locator('#catalogoLocal').input_value()=='patio'
        assert 'preferencia-lista' in page.locator('#itemsGrid').get_attribute('class')
        assert page.locator('.busca-salva').count()==1
        page.evaluate('CatalogoPortal.limpar()');page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===2')
        page.locator('#preferenciasListas summary').click();page.locator('.busca-salva>button').first.click()
        page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===1')
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'catalogo-claro-busca-salva.png'))
        # Trocar de conta no mesmo navegador deve restaurar apenas as preferências próprias.
        page.evaluate("PreferenciasUI.entrar('b@aluno.cps.sp.gov.br')")
        assert page.locator('#searchInput').input_value()=='' and page.locator('.busca-salva').count()==0
        page.evaluate("PreferenciasUI.entrar('a@aluno.cps.sp.gov.br')")
        assert page.locator('#searchInput').input_value()=='garrafa azul' and page.locator('.busca-salva').count()==1
        # Texto vindo do armazenamento é renderizado como texto, não HTML.
        page.evaluate("PreferenciasUI.dados.buscas.push({q:'<img src=x onerror=alert(1)>',status:'TODOS',categoria:'TODOS'});PreferenciasUI.renderizarBuscas()")
        assert page.locator('#buscasSalvasLista img').count()==0
        for width in [320,390,768,1366]:
            page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth&&n.getBoundingClientRect().width>0).slice(0,12).map(n=>[n.tagName,n.id,n.className,n.getBoundingClientRect().right])"))
        page.evaluate("PreferenciasUI.dados.buscas.pop();PreferenciasUI.guardar();PreferenciasUI.sair()")
        assert page.locator('#preferenciasListas').is_hidden() and page.locator('#searchInput').input_value()==''
        assert not errors
    finally:context.close()


def test_preferencias_catalogo_pwa_continuam_salvas_sem_conexao(runtime):
    browser,origin,db=runtime;inserir(db,nome='Estojo azul');context,page,errors=portal(browser,origin)
    try:
        page.evaluate('navigator.serviceWorker.ready');page.wait_for_function('navigator.serviceWorker.controller!==null')
        context.set_offline(True);page.reload();page.wait_for_function("PreferenciasUI.conta!==null && !CatalogoPortal.ocupado")
        assert page.evaluate('CatalogoPortal.ativo') is False
        page.locator('#searchInput').fill('estojo azul')
        page.evaluate("selecionarFiltroCategoria('OUTROS','Outros');selecionarFiltroStatus('DISPONÍVEL','Disponível')")
        page.reload();page.wait_for_function("PreferenciasUI.conta!==null && !CatalogoPortal.ocupado")
        assert page.locator('#searchInput').input_value()=='estojo azul'
        assert page.evaluate('categoriaAtual')=='OUTROS' and page.evaluate('statusAtual')=='DISPONÍVEL'
        assert 'Sem conexão' in page.locator('#catalogoStatus').inner_text()
        assert not errors
    finally:context.close()


def test_secretaria_atalhos_reais_filtros_e_recuperacao_de_falha(runtime):
    browser,origin,db=runtime
    inserir(db,nome='Objeto pendente',aprovado=False);id=inserir(db,nome='Garrafa solicitada',local='Pátio')
    with db() as co:
        with co.cursor() as c:
            c.execute("UPDATE itens SET status='SOLICITADO' WHERE id=%s",(id,))
            c.execute("INSERT INTO mensagens_chat(rm_aluno,nome_aluno,remetente,mensagem,data_envio,email_aluno,lida) VALUES('12345','Aluno','ALUNO','Olá','07/11/2026 12:00','a@aluno.cps.sp.gov.br',FALSE)")
    context,page,errors=admin(browser,origin)
    try:
        page.wait_for_function("document.getElementById('atalhoContagem-pendentes').textContent==='1'")
        assert page.locator('#atalhoContagem-retiradas').inner_text()=='1'
        assert page.locator('#atalhoContagem-mensagens').inner_text()=='1'
        page.locator('main .tema-pergunta').get_by_role('button',name='Prefiro claro',exact=True).click()
        page.get_by_role('button',name='1 Cadastros para analisar',exact=True).click();page.wait_for_selector('#secao-pendentes:not(.hidden)')
        assert page.locator('#moderacaoEstado').input_value()=='PENDENTE'
        page.get_by_role('button',name='1 Retiradas solicitadas',exact=True).click()
        assert page.locator('#secFiltroStatus').input_value()=='SOLICITADO'
        page.locator('#secFiltroLocal').fill('patio');page.locator('#preferenciasListas summary').click();page.get_by_role('button',name='Lista compacta',exact=True).click()
        page.reload();page.wait_for_function("document.getElementById('loginScreen').classList.contains('hidden') && PreferenciasUI.conta!==null")
        assert page.locator('#secFiltroLocal').input_value()=='patio'
        assert page.locator('#secFiltroStatus').input_value()=='SOLICITADO'
        assert 'preferencia-lista' in page.locator('#gridItensContainer').get_attribute('class')
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'secretaria-clara-atalhos.png'))
        page.route('**/api/secretaria/resumo',lambda r:r.fulfill(status=503,json={'success':False}))
        page.get_by_role('button',name='Atualizar atalhos',exact=True).click();page.wait_for_function("document.getElementById('atalhosStatus').textContent.includes('Não foi possível')")
        assert page.locator('#atalhoContagem-pendentes').inner_text()=='—'
        page.unroute('**/api/secretaria/resumo');page.get_by_role('button',name='Atualizar atalhos',exact=True).click();page.wait_for_function("document.getElementById('atalhoContagem-pendentes').textContent==='1'")
        for width in [320,390,768,1366]:
            page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth&&n.getBoundingClientRect().width>0).slice(0,12).map(n=>[n.tagName,n.id,n.className,n.getBoundingClientRect().right])"))
        assert not errors
    finally:context.close()
