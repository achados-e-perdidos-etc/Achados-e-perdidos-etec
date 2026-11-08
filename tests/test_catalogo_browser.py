"""Navegação e moderação web com Flask, PostgreSQL e Chromium de verdade."""
import json,io,time
from pathlib import Path
from PIL import Image
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from tests.test_evolucao_browser import runtime,portal
from tests.test_catalogo_moderacao import inserir

OUT=Path('/workspace/experiencia-evidencias')


def foto_local(route):
    photo=Path('/tmp/etec-preview-assets/item-1.jpg')
    if photo.exists():body=photo.read_bytes()
    else:
        out=io.BytesIO();Image.new('RGB',(640,480),'#526e86').save(out,'JPEG');body=out.getvalue()
    route.fulfill(status=200,body=body,content_type='image/jpeg')


def admin(browser,origin):
    context=browser.new_context(viewport={'width':1366,'height':900},service_workers='block')
    context.add_init_script('sessionStorage.setItem("secretaria_token",'+json.dumps(auth('secretaria@etec.sp.gov.br',True)['Authorization'][7:])+');')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.emulate_media(reduced_motion='reduce');page.goto(origin+'/controle_etec_7788.html')
    page.wait_for_function("tokenSecretaria!==null && document.getElementById('loginScreen').classList.contains('hidden')")
    return context,page,errors


def test_catalogo_paginado_fotos_so_visiveis_filtros_e_navegacao_responsiva(runtime):
    browser,origin,db=runtime
    ids=[inserir(db,nome='Garrafa térmica azul '+str(i)) for i in range(55)]
    context=browser.new_context(viewport={'width':390,'height':844},service_workers='block',has_touch=True)
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true");sessionStorage.setItem("aluno_token",'+json.dumps(auth()['Authorization'][7:])+');sessionStorage.setItem("aluno_dados",JSON.stringify({nome:"Aluno",email:"a@aluno.cps.sp.gov.br",rm:"12345"}));')
    requests=[];context.route('**/image/upload/**',foto_local)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.emulate_media(reduced_motion='reduce')
    try:
        page.goto(origin+'/');page.wait_for_function('CatalogoPortal.ativo && !CatalogoPortal.ocupado');page.wait_for_function("getComputedStyle(document.getElementById('loadingOverlay')).visibility==='hidden'")
        assert page.locator('#itemsGrid>.interactive-card').count()==24
        assert page.locator('#itemsGrid img[src]').count()<24
        assert page.locator('#itemsGrid img[data-src]').count()>0
        assert not any('/api/itens?' in u or u.endswith('/api/itens') for u in requests)
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'catalogo-celular.png'),full_page=False)
        page.locator('#catalogoMais').click();page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===48')
        assert page.locator('#itemsGrid>.interactive-card').count()==48
        page.locator('#searchInput').fill('termica azul 54');page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===1')
        assert str(ids[-1])==str(page.evaluate('todosItens[0].id'))
        assert page.locator('#catalogoFiltrosAtivos button').count()==1
        page.locator('#catalogoFiltrosAtivos button').click();page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===24')
        assert page.locator('#searchInput').input_value()==''
        page.locator('#searchInput').fill('termica azul 54');page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===1')
        page.locator('#itemsGrid>.interactive-card').first.click()
        assert page.locator('#detailScreen').is_visible()
        assert 'presencialmente' in page.locator('#detailProximoPasso').inner_text()
        assert page.locator('#portalBoasVindas').is_hidden()
        assert page.get_by_role('button',name='Voltar ao Catálogo',exact=True).count()==1,page.evaluate("({buttons:[...document.querySelectorAll('#detailScreen button')].map(n=>[n.textContent,n.getAttribute('aria-label'),n.closest('[inert]')?.id]),ativo:Acessibilidade.ativo?.id,modal:[...document.querySelectorAll('[role=dialog]')].filter(n=>getComputedStyle(n).display!=='none').map(n=>n.id)})")
        page.get_by_role('button',name='Voltar ao Catálogo',exact=True).click()
        assert page.locator('#searchInput').input_value()=='termica azul 54'
        page.locator('.ux-nav [data-ux-aba=mural]').click()
        assert page.locator('#muralScreen').is_visible()
        assert page.locator('.ux-nav [aria-current=page]').get_attribute('data-ux-aba')=='mural'
        page.locator('.ux-nav [data-ux-aba=meusItens]').click()
        assert page.locator('#meusItensScreen').is_visible()
        page.locator('.ux-nav [data-ux-aba=catalogo]').click()
        for width in [320,390,768,1366]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),width
        page.set_viewport_size({'width':1366,'height':900});page.locator('#searchInput').fill('');page.wait_for_function('!CatalogoPortal.ocupado && todosItens.length===24');page.evaluate('window.scrollTo(0,0)')
        page.locator('#searchInput').blur();page.screenshot(path=str(OUT/'catalogo-computador.png'),full_page=False)
        page.screenshot(path=str(OUT/'catalogo-completo.png'),full_page=True)
        assert errors==[]
    finally:context.close()


def test_ui_recusa_aluno_corrige_e_secretaria_aprova_preservando_cadastro(runtime):
    browser,origin,db=runtime;context,student,errors=portal(browser,origin);ac,staff,staff_errors=admin(browser,origin)
    try:
        student.evaluate('abrirModalCadastrarAluno()')
        student.locator('#alunoItemNome').fill('Caderno espiral azul')
        student.locator('#alunoItemDesc').fill('Caderno azul com adesivos na capa')
        student.locator('#alunoItemCat').select_option('OUTROS');student.locator('#alunoItemLocal').fill('Pátio')
        student.locator('#btnSalvarAlunoItem').click();student.wait_for_function("document.getElementById('modalCadastrarAluno').classList.contains('hidden')")
        id=scalar(db,'SELECT max(id) FROM itens')
        staff.evaluate("trocarAba('pendentes')")
        staff.get_by_role('button',name='Pedir correção',exact=True).click()
        staff.locator('dialog[open] textarea').fill('Confira a sala em que o caderno foi encontrado.')
        staff.get_by_role('button',name='Enviar motivo ao aluno',exact=True).click()
        staff.wait_for_function("!document.querySelector('dialog[open]')")
        student.evaluate('abrirPainelMeusItens()');student.get_by_role('button',name='Corrigir e reenviar',exact=True).click()
        student.wait_for_function('CorrecaoCadastro.atual!==null')
        assert 'Confira a sala' in student.locator('#motivoCorrecaoCadastro').inner_text()
        assert student.locator('#alunoItemNome').input_value()=='Caderno espiral azul'
        student.locator('#alunoItemLocal').fill('Sala 12');student.locator('#btnSalvarAlunoItem').click()
        student.wait_for_function("document.getElementById('modalCadastrarAluno').classList.contains('hidden')")
        staff.evaluate('ModeracaoUI.carregar()');staff.get_by_role('button',name='Aprovar',exact=True).click()
        staff.wait_for_function("!ModeracaoUI.ocupado && document.querySelector('#gridItensPendentesContainer').textContent.includes('Nenhum cadastro')")
        assert scalar(db,'SELECT count(*) FROM itens')==1
        assert scalar(db,'SELECT aprovado FROM itens WHERE id=%s',(id,)) is True
        assert scalar(db,'SELECT local_encontrado FROM itens WHERE id=%s',(id,))=='Sala 12'
        staff.evaluate('id=>RetiradaSecretaria.historico(id)',id);staff.wait_for_selector('.ev-log')
        assert 'a@aluno.cps.sp.gov.br' in staff.locator('dialog[open]').inner_text()
        assert 'Sala 12' in staff.locator('dialog[open]').inner_text()
        OUT.mkdir(exist_ok=True);staff.screenshot(path=str(OUT/'historico-secretaria.png'),full_page=False)
        assert errors==[] and staff_errors==[]
    finally:context.close();ac.close()


def test_acesso_rotulos_senha_visivel_erro_persistente_e_como_funciona(runtime):
    browser,origin,db=runtime;context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true")')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.emulate_media(reduced_motion='reduce')
    try:
        page.goto(origin+'/');page.wait_for_selector('#loginAlunoScreen:not(.hidden)')
        assert 'professor' in page.locator('#authDescricao').inner_text()
        assert not page.locator('#lembrarLogin').is_checked()
        page.get_by_role('button',name='Mostrar senha',exact=True).click()
        assert page.locator('#loginSenhaAluno').get_attribute('type')=='text'
        page.get_by_role('button',name='Ocultar senha',exact=True).click()
        page.locator('#loginEmailAluno').fill('a@aluno.cps.sp.gov.br');page.locator('#loginSenhaAluno').fill('senha-errada')
        page.locator('#btnAcessoLogin').click();page.wait_for_function('!authOcupada && !document.getElementById("authFeedback").hidden')
        assert page.locator('#authFeedback').get_attribute('role')=='alert'
        assert not page.locator('#loginSenhaAluno').is_disabled()
        OUT.mkdir(exist_ok=True);page.screenshot(path=str(OUT/'login-celular.png'),full_page=False)
        page.get_by_role('button',name='Criar Conta',exact=True).click()
        assert 'Confirme seu e-mail' in page.locator('#authDescricao').inner_text()
        assert page.locator('#authFeedback').is_hidden()
        assert page.locator('#cadSenha').locator('..').get_attribute('class')=='ux-password-wrap'
        assert errors==[]
    finally:context.close()


def test_busca_antiga_nao_substitui_nova_e_falha_nao_anuncia_sucesso(runtime):
    browser,origin,db=runtime;inserir(db,nome='Calculadora Casio')
    context,page,errors=portal(browser,origin)
    try:
        page.wait_for_function('CatalogoPortal.ativo && !CatalogoPortal.ocupado')
        page.evaluate("""()=>{window.fetchReal=window.fetch;window.fetch=async(url,opts)=>{
          if(String(url).includes('/api/catalogo?')&&String(url).includes('q=antiga'))return new Promise(resolve=>window.finalizarAntiga=resolve);
          return window.fetchReal(url,opts);};termoBusca='antiga';window.buscaAntiga=CatalogoPortal.carregar();}""")
        page.wait_for_function('typeof finalizarAntiga===\'function\'')
        page.evaluate("termoBusca='casio';CatalogoPortal.carregar()")
        assert page.evaluate('todosItens[0].nome')=='Calculadora Casio'
        page.evaluate("finalizarAntiga({ok:true,json:async()=>({success:true,itens:[],tem_mais:false,proximo:null})})")
        page.evaluate('window.buscaAntiga')
        assert page.evaluate('todosItens[0].nome')=='Calculadora Casio'
        page.evaluate("""()=>{window.fetch=async(url,opts)=>String(url).includes('/api/catalogo?')?{ok:false,status:503,json:async()=>({success:false,message:'Conexão indisponível.'})}:window.fetchReal(url,opts);return atualizarPortalAluno();}""")
        assert 'Não foi possível atualizar o catálogo' in page.locator('#toastContainer').inner_text()
        assert 'Catálogo atualizado.' not in page.locator('#toastContainer').inner_text()
        assert page.evaluate('todosItens.length')==1
        assert page.locator('#itemsGrid').get_attribute('aria-busy')=='false'
        assert errors==[]
    finally:context.close()
