"""Tk real + PostgreSQL: moderação e contas pessoais usando os mesmos endpoints web."""
import os,time,subprocess,io
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest
from PIL import Image,ImageGrab
from werkzeug.security import generate_password_hash
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,item,codigo,foto
from tests.test_catalogo_moderacao import inserir
import server
import desktop_secretaria as desktop
import desktop_moderacao as equipe
import tkinter as tk


@pytest.fixture
def tela(monkeypatch):
    executable=Path('/tmp/etec-xvfb/usr/bin/Xvfb')
    if not executable.exists():pytest.skip('Xvfb não instalado neste ambiente')
    process=subprocess.Popen([str(executable),':103','-screen','0','1400x1000x24','-nolisten','tcp','-ac'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    monkeypatch.setenv('DISPLAY',':103')
    root=None
    try:
        for _ in range(100):
            try:root=tk.Tk();break
            except tk.TclError:time.sleep(.02)
        assert root is not None
        yield root
    finally:
        if root is not None:
            try:root.destroy()
            except tk.TclError:pass
        process.terminate();process.wait(timeout=5)


def test_desktop_moderacao_professores_login_pessoal_e_revogacao(db,tela,monkeypatch):
    pending=inserir(db,nome='Caderno espiral azul',categoria='OUTROS',aprovado=False,autor='a@aluno.cps.sp.gov.br')
    teacher='docente@etec.sp.gov.br';senha='Senha-local-de-teste-123!'
    with db() as co:
        with co.cursor() as c:
            c.execute('INSERT INTO alunos VALUES(%s,%s,%s,%s)',(teacher,'Docente','PROFESSOR',generate_password_hash(senha)))
            c.execute("INSERT INTO professores_acesso(email,nome,status) VALUES(%s,'Docente','PENDENTE')",(teacher,))
    monkeypatch.setattr(server,'EMAIL_SECRETARIA','secretaria@etec.sp.gov.br');monkeypatch.setattr(server,'ADMIN_SENHA',senha)
    calls=[];messages=[];errors=[]
    tela.report_callback_exception=lambda *args:errors.append(str(args))
    def transport(method,url,**kwargs):
        calls.append((method,urlsplit(url).path));path=urlsplit(url).path
        if '/image/upload/' in path:
            out=io.BytesIO();Image.new('RGB',(30,30),'blue').save(out,'JPEG');return SimpleNamespace(status_code=200,ok=True,content=out.getvalue())
        response=server.app.test_client().open(path+('?' +urlsplit(url).query if urlsplit(url).query else ''),method=method,headers=kwargs.get('headers',{}),json=kwargs.get('json'),data=kwargs.get('data'))
        return SimpleNamespace(status_code=response.status_code,ok=200<=response.status_code<300,json=lambda:response.json,text=response.get_data(as_text=True),content=response.data,headers=response.headers)
    monkeypatch.setattr(desktop.requests,'request',transport)
    from blueprints import uploads
    from services import cloudinary_service
    monkeypatch.setattr(uploads,'get_db_connection',db)
    monkeypatch.setattr(cloudinary_service,'CLOUDINARY_CLOUD_NAME','teste')
    monkeypatch.setattr(cloudinary_service.cloudinary.uploader,'upload',lambda *a,**kw:{'secure_url':'https://res.cloudinary.com/teste/image/upload/'+kw['public_id']+'.jpg'})
    for mod in [desktop,equipe]:
        monkeypatch.setattr(mod.messagebox,'showinfo',lambda *a,**k:messages.append(a))
        monkeypatch.setattr(mod.messagebox,'showerror',lambda *a,**k:errors.append(a))
        monkeypatch.setattr(mod.messagebox,'askyesno',lambda *a,**k:True)
    monkeypatch.setattr(equipe.simpledialog,'askstring',lambda *a,**k:'Confira a sala em que encontrou o caderno.')
    app=desktop.SecretariaApp(tela)
    def aguardar():
        deadline=time.monotonic()+12
        while app.tarefas.ativos and time.monotonic()<deadline:tela.update();time.sleep(.01)
        tela.update();assert not app.tarefas.ativos
    try:
        app.entry_email.insert(0,'secretaria@etec.sp.gov.br');app.entry_senha.insert(0,senha);app.verificar_login();aguardar()
        assert len(app.notebook.tabs())==9 and app.tab_professores is not None
        app.notebook.select(app.tab_moderacao);tela.update();aguardar()
        app.tree_moderacao.selection_set(str(pending));app.recusar_cadastro_desktop();aguardar()
        assert scalar(db,'SELECT motivo_recusa FROM itens WHERE id=%s',(pending,))=='Confira a sala em que encontrou o caderno.'
        correction=server.app.test_client().put(f'/api/meus-cadastros/{pending}',headers=auth(),json={'versao':2,'local':'Sala 12'})
        assert correction.status_code==200,correction.json
        app.carregar_moderacao();aguardar();app.tree_moderacao.selection_set(str(pending));app.aprovar_cadastro_desktop();aguardar()
        assert scalar(db,'SELECT aprovado FROM itens WHERE id=%s',(pending,)) is True
        app.abrir_historico_objeto(pending);aguardar()
        assert not errors
        for widget in tela.winfo_children():
            if isinstance(widget,tk.Toplevel):widget.destroy()
        app.notebook.select(app.tab_professores);tela.update();aguardar()
        app.tree_professores.selection_set(teacher);app.decidir_professor_desktop('APROVAR');aguardar()
        assert scalar(db,'SELECT status FROM professores_acesso WHERE email=%s',(teacher,))=='APROVADO'
        out=Path('/workspace/experiencia-evidencias');out.mkdir(exist_ok=True);ImageGrab.grab(xdisplay=':103').save(out/'desktop-professores.png')
        # Paridade nativa: filtros, rascunho, categoria, relatório e retirada com aceite.
        def filhos(widget):
            for filho in widget.winfo_children():yield filho;yield from filhos(filho)
        monkeypatch.setattr('utils.comprovantes.webbrowser.open',lambda *a,**k:True)
        app.notebook.select(app.tab_itens);tela.update()
        app.filtros_estoque['q'].insert(0,'caderno');app.filtros_estoque['local'].insert(0,'sala');app.aplicar_filtros_tabela()
        assert len(app.tree_itens.get_children())==1
        app.limpar_filtros_estoque()
        form=app.abrir_modal_form();form.campos['nome'].insert(0,'Rascunho preservado');form.fechar()
        form=app.abrir_modal_form();assert form.campos['nome'].get()=='Rascunho preservado';form.fechar()
        app.rascunho_item=None
        form=app.abrir_modal_form()
        for chave,valor in [('nome','Garrafa desktop'),('descricao','Garrafa azul com tampa'),('local','Biblioteca')]:form.campos[chave].insert(0,valor)
        form.upload.adicionar(foto());aguardar();form.salvar();aguardar()
        assert scalar(db,"SELECT count(*) FROM itens WHERE nome_item='Garrafa desktop'")==1
        assert scalar(db,"SELECT foto FROM itens WHERE nome_item='Garrafa desktop'").startswith('https://')
        assert app.rascunho_item is None
        app.entry_cat.insert(0,'PARIDADE');app.adicionar_categoria();aguardar()
        app.listbox_cats.selection_clear(0,'end');app.listbox_cats.selection_set(app.categorias_atuais.index('PARIDADE'));app.remover_categoria_desktop();aguardar()
        assert 'PARIDADE' not in app.categorias_atuais
        app.documento_desktop('COMPLETO');aguardar()
        assert 'Caderno espiral azul' in (Path(app.impressoes_temporarias[-1].name)/'documento.html').read_text()
        app.limpar_impressoes()
        retirada=item(db);code=codigo(server.app.test_client(),retirada)
        app.abrir_retirada_codigo();janela=next(w for w in tela.winfo_children() if isinstance(w,tk.Toplevel) and w.title()=='Confirmar retirada com código')
        entries=[w for w in filhos(janela) if w.winfo_class()=='TEntry']
        for campo,valor in zip(entries,[str(retirada),code,'Aluno de Teste']):campo.insert(0,valor)
        next(w for w in filhos(janela) if w.winfo_class()=='Checkbutton').invoke()
        next(w for w in filhos(janela) if w.winfo_class()=='TButton' and w.cget('text')=='Usar nome digitado').invoke()
        next(w for w in filhos(janela) if w.winfo_class()=='TButton' and w.cget('text')=='Confirmar entrega').invoke();aguardar()
        assert scalar(db,'SELECT status FROM itens WHERE id=%s',(retirada,))=='ENTREGUE'
        assert scalar(db,"SELECT metodo FROM entregues WHERE item_id=%s",(retirada,))=='CODIGO'
        pro=Path('/workspace/paridade-evidencias');pro.mkdir(exist_ok=True);ImageGrab.grab(xdisplay=':103').save(pro/'desktop-retirada-codigo.png')
        janela.destroy();assert not errors
        app.encerrar_sessao();app.entry_email.insert(0,teacher);app.entry_senha.insert(0,senha);app.verificar_login();aguardar()
        assert len(app.notebook.tabs())==8 and app.tab_professores is None
        assert app.perfil_painel['perfil']=='moderador'
        assert ('POST','/api/auth/login-aluno') in calls
        with db() as co:
            with co.cursor() as c:c.execute("UPDATE professores_acesso SET status='REVOGADO' WHERE email=%s",(teacher,))
        app.carregar_moderacao();aguardar()
        assert not app.pendentes_desktop or app.var_status.get()
        assert server.app.test_client().get('/api/moderacao/cadastros',headers={'Authorization':'Bearer '+desktop.TOKEN_SECRETARIA}).status_code==403
        assert not errors
        # O comprovante do aplicativo abre impressão no navegador, sem enviar à impressora durante o teste.
        monkeypatch.setattr('utils.comprovantes.webbrowser.open',lambda *a,**k:True)
        app.abrir_tela_comprovante(7,'Estojo azul','Estojo','Sala','Aluno Teste','12345','DS')
        def filhos(widget):
            for filho in widget.winfo_children():yield filho;yield from filhos(filho)
        botao=next(w for w in filhos(tela) if w.winfo_class()=='Button' and w.cget('text')=='Imprimir comprovante')
        botao.invoke();aguardar()
        assert len(app.impressoes_temporarias)==1
        arquivo=Path(app.impressoes_temporarias[0].name)/'comprovante.html'
        assert arquivo.exists() and 'Estojo azul' in arquivo.read_text()
        app.encerrar_sessao();assert not arquivo.exists()
        assert not errors
    finally:app.tarefas.fechar();app.limpar_impressoes();app.limpar_recursos_paridade()
