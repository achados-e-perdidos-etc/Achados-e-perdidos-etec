"""Formulário curto, teclado/viewport reduzido e contraste nos dois temas."""
import pytest
from tests.test_push_delivery_postgres import postgres,db_env
from tests.test_push_delivery import configured
from tests.test_evolucao import db
from tests.test_evolucao_browser import runtime,portal
from tests.test_catalogo_browser import admin


def contraste(page,selector):
    return page.locator(selector).first.evaluate('''n=>{
      const rgb=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number);
      const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
      let pai=n;while(pai&&getComputedStyle(pai).backgroundColor==='rgba(0, 0, 0, 0)')pai=pai.parentElement;
      const a=lum(rgb(getComputedStyle(n).color)),b=lum(rgb(getComputedStyle(pai||document.body).backgroundColor));
      return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    }''')


@pytest.mark.parametrize('tema',['claro','escuro'])
def test_formulario_aluno_erros_preservam_texto_e_cabem_no_teclado(runtime,tema):
    browser,origin,db=runtime;context,page,errors=portal(browser,origin)
    try:
        page.evaluate('t=>TemaUI.escolher(t)',tema);page.evaluate('abrirModalCadastrarAluno()')
        page.locator('#alunoItemNome').fill('Estojo azul')
        page.locator('#btnSalvarAlunoItem').click()
        assert page.locator('#alunoItemNome').input_value()=='Estojo azul'
        assert page.locator('#alunoItemDesc').get_attribute('aria-invalid')=='true'
        assert 'Preencha' in page.locator('#ux-erro-alunoItemDesc').inner_text()
        assert contraste(page,'#ux-erro-alunoItemDesc')>=4.5
        page.locator('#alunoItemDesc').fill('Estojo azul com zíper')
        assert page.locator('#ux-erro-alunoItemDesc').count()==0
        for width,height in [(320,568),(390,360),(768,500),(1366,900)]:
            page.set_viewport_size({'width':width,'height':height})
            campo=page.locator('#alunoItemLocal');campo.focus();campo.scroll_into_view_if_needed()
            assert campo.is_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            rect=page.locator('#modalCadastrarAluno>.glass-panel').bounding_box()
            assert rect['height']<=height-30
            page.locator('#btnSalvarAlunoItem').scroll_into_view_if_needed()
            assert page.locator('#btnSalvarAlunoItem').bounding_box()['y']>=0
        assert not errors
    finally:context.close()


@pytest.mark.parametrize('tema',['claro','escuro'])
def test_secretaria_login_erros_e_contraste_do_painel(runtime,tema):
    browser,origin,db=runtime;context,page,errors=admin(browser,origin)
    try:
        page.evaluate('t=>TemaUI.escolher(t)',tema)
        for selector in ['.header-titulo','.status-sessao','.paridade-filtros label','.secretaria-atalhos button span']:
            assert contraste(page,selector)>=4.5,(tema,selector,contraste(page,selector))
        page.evaluate("document.getElementById('loginScreen').classList.remove('hidden')")
        page.locator('#loginEmailInput').fill('incompleto');page.locator('#btnLoginSec').click()
        assert page.locator('#loginEmailInput').get_attribute('aria-invalid')=='true'
        assert page.locator('#ux-erro-loginEmailInput').inner_text()=='Digite um e-mail válido.'
        page.locator('#loginEmailInput').fill('secretaria@etec.sp.gov.br')
        assert page.locator('#ux-erro-loginEmailInput').count()==0
        assert not errors
    finally:context.close()
