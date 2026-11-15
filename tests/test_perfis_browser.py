"""Termos por teclado/toque e fotos privadas com navegador e servidor reais."""
from pathlib import Path
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,item
from tests.test_evolucao_browser import runtime,portal
from tests.test_catalogo_browser import admin,foto_local
from tests.test_catalogo_moderacao import inserir
from tests.test_acabamento_browser import contraste
from tests.test_perfis_termos import ROSTO,uri,dados_cadastro
from utils.perfis import VERSAO_TERMOS
import server

OUT=Path('/workspace/perfil-termos-evidencias')


def cadastro_aberto(browser,origin):
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,service_workers='block')
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true")')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.emulate_media(reduced_motion='reduce');page.goto(origin+'/')
    page.wait_for_selector('#loginAlunoScreen:not(.hidden)')
    page.get_by_role('button',name='Criar Conta',exact=True).click()
    # Código sem SMTP externo, já preparado no banco temporário.
    page.evaluate("document.getElementById('passo1Cadastro').classList.add('hidden');document.getElementById('passo2Cadastro').classList.remove('hidden')")
    page.wait_for_function('TermosUI.dados!==null')
    return context,page,errors


def test_termos_obrigam_fim_do_texto_e_aceite_explicito_antes_do_cadastro(runtime):
    browser,origin,db=runtime;payload=dados_cadastro(db);context,page,errors=cadastro_aberto(browser,origin)
    try:
        check=page.locator('#aceiteTermos');assert check.is_disabled() and not check.is_checked()
        page.locator('#cadEmailAluno').evaluate('(n,email)=>n.value=email',payload['email'])
        for id,chave in [('cadNome','nome'),('cadRM','rm'),('cadCodigo','codigo'),('cadSenha','senha')]:page.locator('#'+id).fill(payload[chave])
        # Mesmo uma chamada direta ao handler não pula o requisito da leitura.
        page.evaluate('confirmarCadastro({preventDefault(){}})')
        assert scalar(db,'SELECT count(*) FROM termos_aceites')==0
        page.locator('#lerTermos').click();texto=page.locator('.termos-leitura')
        assert texto.evaluate('n=>n.scrollHeight>n.clientHeight')
        texto.focus();page.keyboard.press('PageDown');assert check.is_disabled()
        page.get_by_role('button',name='Voltar ao cadastro',exact=True).click();assert check.is_disabled()
        page.locator('#lerTermos').click();texto.focus();page.keyboard.press('Control+End')
        page.wait_for_function("!document.getElementById('aceiteTermos').disabled")
        assert not check.is_checked()
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'termos-leitura-celular.png'))
        page.get_by_role('button',name='Voltar ao cadastro',exact=True).click()
        page.get_by_role('button',name='Finalizar Cadastro',exact=True).click()
        assert scalar(db,'SELECT count(*) FROM termos_aceites')==0
        check.check();page.get_by_role('button',name='Finalizar Cadastro',exact=True).click()
        page.wait_for_function("alunoSessao?.email==='novo@aluno.cps.sp.gov.br'")
        assert scalar(db,'SELECT versao FROM termos_aceites')==VERSAO_TERMOS
        assert scalar(db,'SELECT count(*) FROM codigos_auth')==0
        assert check.is_disabled() and not check.is_checked()
        assert not errors
    finally:context.close()


def test_termos_rolagem_por_toque_e_nova_versao_bloqueia_novamente(runtime):
    browser,origin,db=runtime;context,page,errors=cadastro_aberto(browser,origin)
    try:
        page.set_viewport_size({'width':320,'height':650});page.locator('#lerTermos').click()
        texto=page.locator('.termos-leitura');bounds=texto.bounding_box();cdp=context.new_cdp_session(page)
        for _ in range(24):
            if not page.locator('#aceiteTermos').is_disabled():break
            x=bounds['x']+bounds['width']/2;inicio=bounds['y']+bounds['height']-15
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':inicio}]})
            for passo in range(1,9):
                cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':inicio-(bounds['height']-30)*passo/8}]})
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        assert not page.locator('#aceiteTermos').is_disabled(),texto.evaluate('n=>({scroll:n.scrollTop,altura:n.clientHeight,total:n.scrollHeight,bounds:n.getBoundingClientRect().toJSON(),alvo:document.elementFromPoint(n.getBoundingClientRect().x+30,n.getBoundingClientRect().y+30)?.outerHTML.slice(0,130)})')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.get_by_role('button',name='Voltar ao cadastro',exact=True).click();page.locator('#aceiteTermos').check()
        page.route('**/api/termos',lambda r:r.fulfill(json={'success':True,'versao':'versao-nova','secoes':[{'titulo':'Novo texto','texto':'Releia os termos atualizados. '*100}]}))
        page.locator('#lerTermos').click();page.wait_for_function("TermosUI.dados?.versao==='versao-nova'")
        assert page.locator('#aceiteTermos').is_disabled() and not page.locator('#aceiteTermos').is_checked()
        assert not errors
    finally:context.close()


def test_upload_remover_e_logout_nao_deixam_foto_anterior(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        page.get_by_role('button',name='Abrir meu perfil',exact=True).click()
        page.get_by_role('button',name='Minha foto de perfil',exact=True).click()
        dialog=page.locator('dialog.perfil-privado');assert 'opcional' in dialog.inner_text()
        assert dialog.locator('.perfil-previa').is_hidden()
        dialog.locator('input[type=file]').set_input_files(ROSTO)
        assert 'ainda não foi salva' in dialog.locator('[role=status]').inner_text()
        dialog.get_by_role('button',name='Salvar foto',exact=True).click()
        page.wait_for_function('PerfilUI.proprio?.foto_id && PerfilUI.url!==null')
        assert scalar(db,'SELECT count(*) FROM perfis_fotos')==1
        assert page.locator('.perfil-avatar').get_attribute('src').startswith('blob:')
        assert not page.evaluate("JSON.stringify({...localStorage,...sessionStorage}).includes('blob:')")
        dialog.get_by_role('button',name='Remover minha foto',exact=True).click()
        page.wait_for_function('PerfilUI.url===null');assert page.locator('.perfil-avatar').is_hidden()
        dialog.locator('input[type=file]').set_input_files(ROSTO);dialog.get_by_role('button',name='Salvar foto',exact=True).click()
        page.wait_for_function('PerfilUI.url!==null');page.evaluate('fazerLogoff(false)')
        assert page.locator('dialog.perfil-privado').count()==0
        assert page.locator('.perfil-avatar').get_attribute('src') is None
        assert not errors
    finally:context.close()


def test_secretaria_consulta_foto_no_objeto_e_retirada_e_contraste_claro(runtime):
    browser,origin,db=runtime;id=item(db)
    server.app.test_client().post('/api/perfil/foto',headers=auth(),json={'foto':uri(ROSTO.read_bytes())})
    context,page,errors=admin(browser,origin)
    try:
        page.wait_for_function('id=>itensSec.some(i=>i.id===id)',arg=id)
        page.evaluate('id=>abrirDetalhesItem(id)',id)
        page.get_by_role('button',name='Ver perfil do solicitante',exact=True).click()
        page.wait_for_selector('dialog.perfil-privado img')
        assert 'a@aluno.cps.sp.gov.br' in page.locator('dialog.perfil-privado').inner_text()
        page.locator('dialog .ev-close').click();page.evaluate("document.getElementById('modalDetalhesItem').classList.add('hidden')")
        page.evaluate('RetiradaSecretaria.abrir()');page.get_by_label('Número do objeto',exact=True).fill(str(id))
        page.get_by_role('button',name='Ver perfil do solicitante',exact=True).click();page.wait_for_selector('dialog.perfil-privado img')
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'secretaria-perfil.png'))
        assert not errors
    finally:context.close()
    inserir(db)
    context,page,errors=portal(browser,origin);context.route('**/image/upload/**',foto_local)
    try:
        page.evaluate("document.documentElement.dataset.tema='claro'")
        page.wait_for_selector('#itemsGrid .ux-card-image')
        # Cores computadas, incluindo a especificidade do tema e do Tailwind locais.
        cores=page.locator('#itemsGrid .ux-card-image .left-2\\.5 span').first.evaluate('n=>[getComputedStyle(n).color,getComputedStyle(n).backgroundColor]')
        assert cores==['rgb(255, 255, 255)','rgb(25, 35, 52)'],cores
        assert contraste(page,'#itemsGrid .ux-card-image .left-2\\.5 span')>=4.5
        assert page.locator('.ux-card-view').first.evaluate('n=>getComputedStyle(n).color')=='rgb(165, 22, 38)'
        assert contraste(page,'.ux-card-view')>=4.5
        page.evaluate('abrirModalCadastrarAluno()')
        assert page.locator('#modalCadastrarAluno label').first.evaluate('n=>getComputedStyle(n).color')=='rgb(75, 91, 112)'
        assert page.locator('#modalCadastrarAluno .ux-field-help').evaluate('n=>getComputedStyle(n).color')=='rgb(75, 91, 112)'
        assert contraste(page,'#modalCadastrarAluno .ux-field-help')>=4.5
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'cadastro-contraste-claro.png'))
        assert not errors
    finally:context.close()
