"""Prioridades privadas e preferências locais isoladas por identidade."""
import json
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from tests.test_catalogo_moderacao import inserir
from utils import preferencias_desktop
import server


def test_resumo_privado_conta_fila_retiradas_e_mensagens_recentes(db):
    a=inserir(db,nome='Pendente',aprovado=False);b=inserir(db,nome='Corrigir',aprovado=False)
    retirar=inserir(db,nome='Solicitado');inserir(db,nome='Disponível')
    with db() as co:
        with co.cursor() as c:
            c.execute("UPDATE itens SET recusado_em=NOW(),motivo_recusa='Corrigir local' WHERE id=%s",(b,))
            c.execute("UPDATE itens SET status='SOLICITADO' WHERE id=%s",(retirar,))
            for remetente,lida,idade in [('ALUNO',False,0),('ALUNO',False,0),('ALUNO',True,0),('SECRETARIA',False,0),('ALUNO',False,31)]:
                c.execute("INSERT INTO mensagens_chat(rm_aluno,nome_aluno,remetente,mensagem,data_envio,email_aluno,lida,criada_em) VALUES('12345','Aluno',%s,'Mensagem de teste','07/11/2026 12:00','a@aluno.cps.sp.gov.br',%s,NOW()-%s*INTERVAL '1 day')",(remetente,lida,idade))
    client=server.app.test_client();url='/api/secretaria/resumo'
    assert client.get(url).status_code==401
    assert client.get(url,headers=auth()).status_code==403
    res=client.get(url,headers=auth('secretaria@etec.sp.gov.br',True))
    assert res.status_code==200 and res.json==dict(success=True,pendentes=1,retiradas=1,mensagens=2)
    assert 'no-store' in res.headers['Cache-Control']
    with db() as co:
        with co.cursor() as c:c.execute('UPDATE mensagens_chat SET lida=TRUE')
    assert client.get(url,headers=auth('secretaria@etec.sp.gov.br',True)).json['mensagens']==0
    with db() as co:
        with co.cursor() as c:
            c.execute("INSERT INTO alunos VALUES('docente@etec.sp.gov.br','Docente','PROFESSOR','hash-ficticio')")
            c.execute("INSERT INTO professores_acesso(email,nome,status) VALUES('docente@etec.sp.gov.br','Docente','APROVADO')")
    docente=auth('docente@etec.sp.gov.br')
    # A mesma checagem de acesso delegado vale para o resumo, inclusive após revogação.
    assert client.get(url,headers=docente).status_code==200
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE professores_acesso SET status='REVOGADO' WHERE email='docente@etec.sp.gov.br'")
    assert client.get(url,headers=docente).status_code==403


def test_preferencias_desktop_so_campos_permitidos_e_contas_separadas(tmp_path,monkeypatch):
    monkeypatch.setenv('ETEC_PREFERENCIAS_DIR',str(tmp_path))
    assert preferencias_desktop.salvar('a@escola',{'filtros':{'q':'garrafa azul','status':'SOLICITADO','senha':'segredo'},'larguras':{'Objeto':20000},'token':'segredo'})
    assert preferencias_desktop.ler('A@escola')=={'filtros':{'q':'garrafa azul','status':'SOLICITADO'},'larguras':{'Objeto':600}}
    assert preferencias_desktop.ler('b@escola')=={}
    raw=preferencias_desktop.caminho('a@escola').read_text();assert 'segredo' not in raw
    preferencias_desktop.caminho('a@escola').write_text('{corrompido')
    assert preferencias_desktop.ler('a@escola')=={}


def test_preferencias_desktop_falha_de_disco_preserva_arquivo(tmp_path,monkeypatch):
    monkeypatch.setenv('ETEC_PREFERENCIAS_DIR',str(tmp_path));assert preferencias_desktop.salvar('a',{'filtros':{'q':'original'}})
    def falhar(*a):raise OSError('disco indisponível')
    monkeypatch.setattr(preferencias_desktop.os,'replace',falhar)
    assert not preferencias_desktop.salvar('a',{'filtros':{'q':'alterado'}})
    assert preferencias_desktop.ler('a')['filtros']['q']=='original'
    assert len(list(tmp_path.iterdir()))==1
