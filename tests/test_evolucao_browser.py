"""Flask + PostgreSQL + Chromium: fluxos reais, somente armazenamento externo simulado."""
import io,json,threading
from pathlib import Path
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,foto,item
from blueprints import uploads,notificacoes,cadastros
from services import cloudinary_service
import server


@pytest.fixture
def runtime(db,monkeypatch):
    for mod in [uploads,notificacoes,cadastros]:monkeypatch.setattr(mod,'get_db_connection',db)
    monkeypatch.setattr(cloudinary_service,'CLOUDINARY_CLOUD_NAME','teste')
    monkeypatch.setattr(cloudinary_service.cloudinary.uploader,'upload',lambda *args,**kw:{'secure_url':'https://res.cloudinary.com/teste/image/upload/'+kw['public_id']+'.jpg'})
    server.app.config['TESTING']=True;server.app.config['PUSH_AUTOSTART']=False
    http=make_server('127.0.0.1',0,server.app,threaded=True);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        yield browser,'http://127.0.0.1:'+str(http.server_port),db
        browser.close()
    http.shutdown();thread.join(timeout=3)


def portal(browser,origin):
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true");sessionStorage.setItem("aluno_token",'+json.dumps(auth()['Authorization'][7:])+');sessionStorage.setItem("aluno_dados",'+json.dumps(json.dumps({'nome':'Aluno','email':'a@aluno.cps.sp.gov.br','rm':'12345'}))+');')
    page=context.new_page();page.emulate_media(reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin+'/');page.wait_for_function("typeof alunoSessao!=='undefined' && alunoSessao?.email==='a@aluno.cps.sp.gov.br'")
    page.wait_for_function("document.getElementById('alunoItemCat').options.length>0")
    return context,page,errors


def test_pwa_reabre_offline_formulario_real_e_sincroniza_sem_duplicar(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        page.evaluate('navigator.serviceWorker.ready')
        page.wait_for_function('navigator.serviceWorker.controller!==null')
        context.set_offline(True);page.reload()
        page.wait_for_function("document.getElementById('loginAlunoScreen').classList.contains('hidden')")
        assert page.locator('#alunoItemCat option').count()>0
        page.wait_for_function("getComputedStyle(document.getElementById('loadingOverlay')).visibility==='hidden'")
        assert page.locator('#gifSplash').get_attribute('src') is None
        page.evaluate('abrirModalCadastrarAluno()')
        page.locator('#alunoItemNome').fill('Estojo offline')
        page.locator('#alunoItemDesc').fill('Estojo preto com zíper azul')
        page.locator('#alunoItemCat').select_option('OUTROS')
        page.locator('#alunoItemLocal').fill('Biblioteca')
        page.locator('#offlineConsent-encontrado').check()
        page.locator('#btnSalvarAlunoItem').click()
        page.wait_for_function("document.getElementById('modalCadastrarAluno').classList.contains('hidden')")
        assert page.evaluate('FilaOffline.listar().then(r=>r.length)')==1
        assert scalar(db,'SELECT count(*) FROM itens')==0
        context.set_offline(False)
        page.evaluate('FilaOffline.sincronizar()')
        page.wait_for_function('!FilaOffline.busy')
        assert page.evaluate('FilaOffline.listar().then(r=>r.length)')==0
        assert scalar(db,'SELECT count(*) FROM itens')==1
        assert scalar(db,'SELECT aprovado FROM itens') is False
        page.evaluate('FilaOffline.sincronizar()')
        assert scalar(db,'SELECT count(*) FROM itens')==1
        assert errors==[]
    finally:context.close()


def test_fila_com_fotos_retoma_e_perda_da_resposta_nao_duplica(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        context.set_offline(True)
        page.evaluate('(foto)=>FilaOffline.guardar("encontrado",{nome:"Objeto na fila",descricao:"Estojo preto",categoria:"OUTROS",local:"Pátio",data:new Date().toLocaleDateString("pt-BR"),fotos:[foto]})',foto())
        # A primeira resposta se perde depois de o servidor confirmar a transação.
        page.evaluate('''() => {const original=window.fetch;let lost=false;window.fetch=async(url,options)=>{
          const r=await original(url,options);if(!lost&&String(url).endsWith('/api/itens/cadastrar-aluno')){lost=true;throw Error('Resposta perdida');}return r;};}''')
        context.set_offline(False)
        page.evaluate('FilaOffline.sincronizar()')
        page.wait_for_function('!FilaOffline.busy')
        assert scalar(db,'SELECT count(*) FROM itens')==1
        assert page.evaluate('FilaOffline.listar().then(r=>r.length)')==1
        page.evaluate('FilaOffline.sincronizar()')
        assert page.evaluate('FilaOffline.listar().then(r=>r.length)')==0
        assert scalar(db,'SELECT count(*) FROM itens')==1
        assert scalar(db,'SELECT count(*) FROM uploads_fotos')==1
        assert errors==[]
    finally:context.close()


def test_fila_isolada_expira_e_saida_remove_fotos_sem_tokens(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        context.set_offline(True)
        payload={'nome':'Estojo A','descricao':'Descrição','categoria':'OUTROS','fotos':[foto()]}
        page.evaluate('p=>FilaOffline.guardar("encontrado",p)',payload)
        assert page.evaluate('FilaOffline.listar().then(rows=>Object.keys(rows[0]))')==['id','email','tipo','payload','criado','erro']
        page.evaluate("sessionStorage.setItem('aluno_dados',JSON.stringify({nome:'Aluno B',email:'b@aluno.cps.sp.gov.br',rm:'12345'}))")
        page.evaluate('FilaOffline.mostrar()')
        assert 'Nenhum envio pendente' in page.locator('.evolucao-dialog').inner_text()
        page.locator('.ev-close').click()
        page.evaluate("sessionStorage.setItem('aluno_dados',JSON.stringify({nome:'Aluno',email:'a@aluno.cps.sp.gov.br',rm:'12345'}))")
        page.evaluate('''async()=>{const rows=await FilaOffline.listar();rows[0].criado=Date.now()-25*3600000;await FilaOffline.transacao('readwrite',s=>s.put(rows[0]));}''')
        assert page.evaluate('FilaOffline.listar().then(rows=>rows.length)')==0
        page.evaluate('p=>FilaOffline.guardar("encontrado",p)',payload)
        page.evaluate('fazerLogoff(false)')
        assert page.evaluate('FilaOffline.listar().then(rows=>rows.length)')==0
        assert page.evaluate('SessaoPortal.token()') is None
        assert errors==[]
    finally:context.close()


def test_aluno_obtem_codigo_secretaria_confirma_aceite_e_consulta_historico(runtime):
    browser,origin,db=runtime;id=item(db);context,page,errors=portal(browser,origin)
    try:
        page.evaluate('id=>RetiradasAluno.mostrar(id)',id)
        page.wait_for_selector('.ev-code');code=page.locator('.ev-code').inner_text()
        assert len(code)==6
        output=Path('/workspace/evolucao-evidencias');output.mkdir(exist_ok=True)
        page.screenshot(path=str(output/'aluno-codigo-retirada.png'),full_page=True)
        page.locator('.ev-close').click()
        page.goto(origin+'/controle_etec_7788.html')
        page.evaluate('t=>{tokenSecretaria=t;sessionStorage.setItem("secretaria_token",t);document.getElementById("loginScreen").classList.add("hidden");}',auth('secretaria@etec.sp.gov.br',True)['Authorization'][7:])
        page.evaluate('RetiradaSecretaria.abrir()')
        page.get_by_label('Número do objeto',exact=True).fill(str(id))
        page.get_by_label('Código de seis dígitos',exact=True).fill(code)
        page.get_by_label('Conferi presencialmente',exact=False).check()
        page.get_by_label('Se não puder desenhar',exact=False).fill('Aluno Teste da Escola')
        page.get_by_role('button',name='Usar nome digitado',exact=True).click()
        page.screenshot(path=str(output/'secretaria-aceite-retirada.png'),full_page=True)
        page.get_by_role('button',name='Confirmar entrega',exact=True).click()
        page.wait_for_function("document.querySelector('.evolucao-dialog [role=status]').textContent.includes('Entrega confirmada')")
        assert scalar(db,'SELECT count(*) FROM entregues')==1
        page.locator('.ev-close').click();page.evaluate('RetiradaSecretaria.historico()')
        page.locator('dialog[open]').get_by_label('Número do objeto',exact=True).fill(str(id));page.get_by_role('button',name='Consultar',exact=True).click()
        page.wait_for_selector('.ev-log')
        assert 'secretaria@etec.sp.gov.br' in page.locator('.ev-log').first.inner_text()
        page.screenshot(path=str(output/'secretaria-auditoria.png'),full_page=True)
        assert errors==[]
    finally:context.close()


def test_revisao_visual_nao_altera_conta_e_respeita_campos_manuais(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        page.evaluate('abrirModalCadastrarAluno()')
        page.locator('#alunoItemNome').fill('Preenchido manualmente')
        page.evaluate("RevisaoVisual.mostrar({cores:['azul','branco'],ocr_confianca:'baixa',ocr_rm:'99999',ocr_nome_aluno:'Nome incorreto'},'aluno')")
        box=page.locator('#revisaoVisual-aluno')
        assert 'baixa confiança' in box.inner_text()
        assert box.locator('input').first.input_value()==''
        assert page.locator('#alunoItemNome').input_value()=='Preenchido manualmente'
        assert page.evaluate('SessaoPortal.dados().rm')=='12345'
        assert errors==[]
    finally:context.close()
