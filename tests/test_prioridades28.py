from unittest.mock import patch
import pytest
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_portal_updates_postgres import db,db_cadastros,auth
from services.chat_retencao import limpar_expiradas
from flask import Flask
from blueprints import chat,itens,relatorios
import server

@pytest.fixture(params=['unificado','modular'])
def client(request,db_cadastros,monkeypatch):
    monkeypatch.setattr(relatorios,"get_db_connection",db_cadastros)
    app=server.app
    if request.param=='modular':
        app=Flask(__name__)
        for bp in [chat.chat_bp,itens.itens_bp,relatorios.relatorios_bp]:app.register_blueprint(bp)
    app.config['TESTING']=True
    return app.test_client()
SEC={'Authorization':'Bearer '+server.gerar_token_secretaria('secretaria@etec.sp.gov.br')}
A='a@aluno.cps.sp.gov.br';B='b@aluno.cps.sp.gov.br'

def test_chat_contas_com_rm_igual_e_legado(client,db_cadastros):
    for email,msg in [(A,'Só A'),(B,'Só B')]:assert client.post('/api/chat/enviar',headers=auth(email),json={'mensagem':msg,'email':B}).status_code==200
    for email,msg in [(A,'Só A'),(B,'Só B')]:assert [m['mensagem'] for m in client.get('/api/chat/mensagens/12345',headers=auth(email)).json]==[msg]
    assert client.post('/api/chat/enviar',headers=SEC,json={'rm':'12345','mensagem':'sem conta'}).status_code==409
    assert client.post('/api/chat/enviar',headers=SEC,json={'email':A,'mensagem':'Resposta A'}).status_code==200
    assert len(client.get('/api/chat/mensagens/12345',headers=auth(B)).json)==1
    with db_cadastros() as co:
        with co.cursor() as c:c.execute("INSERT INTO mensagens_chat (rm_aluno,nome_aluno,remetente,mensagem,data_envio) VALUES ('12345','Antigo','SECRETARIA','Sem autoria','hoje')")
    assert len(client.get('/api/chat/mensagens/12345',headers=auth(A)).json)==2
    assert client.get('/api/chat/legado/12345',headers=auth(A)).status_code==403
    assert client.get('/api/chat/legado/12345',headers=SEC).json[0]['mensagem']=='Sem autoria'
    rows=client.get('/api/chat/conversas',headers=SEC).json
    assert len(rows)==3 and sum(r['legado'] for r in rows)==1
    assert client.get('/api/chat/mensagens/12345?email='+B,headers=auth(A)).status_code==403

def test_reversao_preserva_auditoria_sem_contar_duas_entregas(client,db_cadastros):
    assert client.post('/api/itens',headers=SEC,json={'nome':'Estojo','descricao':'Estojo azul'}).status_code==200
    item=scalar(db_cadastros,'SELECT MAX(id) FROM itens')
    for _ in range(2):assert client.put(f'/api/itens/{item}',headers=SEC,json={'status':'ENTREGUE'}).status_code==200
    assert len(client.get('/api/entregues',headers=SEC).json)==1
    for _ in range(2):assert client.put(f'/api/itens/{item}/recusar',headers=SEC).status_code==200
    assert client.get('/api/entregues',headers=SEC).json==[]
    rows=client.get('/api/entregues?incluir_canceladas=true',headers=SEC).json
    assert len(rows)==1 and rows[0]['cancelada_em'] and rows[0]['cancelada_por']=='secretaria@etec.sp.gov.br'
    assert client.get('/api/estatisticas',headers=SEC).json['total_entregues']==0
    assert client.put(f'/api/itens/{item}',headers=SEC,json={'status':'ENTREGUE'}).status_code==200
    assert len(client.get('/api/entregues?incluir_canceladas=true',headers=SEC).json)==2

@pytest.mark.parametrize('dados',[{},[],{'nome':'X','descricao':''},{'nome':17,'descricao':'ok'},{'nome':'x','descricao':'ok','data':'31/02/2026'},{'nome':'x','descricao':'ok','categoria':'inexistente'},{'nome':'x'*151,'descricao':'ok'}])
def test_validacao_antes_de_fotos(client,db_cadastros,dados):
    with patch.object(server,'processar_fotos') as f,patch.object(itens,'processar_fotos') as g:
        assert client.post('/api/itens/cadastrar-aluno',headers=auth(),json=dados).status_code==400
        f.assert_not_called();g.assert_not_called()
    assert scalar(db_cadastros,'SELECT count(*) FROM itens')==0

def test_retencao_sem_apagar_contas(client,db_cadastros):
    for email in [A,B]:assert client.post('/api/chat/enviar',headers=auth(email),json={'mensagem':'nova','criada_em':'2000-01-01'}).status_code==200
    with db_cadastros() as co:
        with co.cursor() as c:
            c.execute("INSERT INTO mensagens_chat (rm_aluno,nome_aluno,remetente,mensagem,data_envio,criada_em) VALUES ('12345','Antigo','SECRETARIA','velha','hoje',CURRENT_TIMESTAMP-INTERVAL '31 days')")
            c.execute("UPDATE mensagens_chat SET criada_em=CURRENT_TIMESTAMP-INTERVAL '29 days' WHERE email_aluno=%s",(B,))
    assert client.get('/api/chat/legado/12345',headers=SEC).json==[]
    assert limpar_expiradas(db_cadastros,limite=1,lotes=5)==1
    assert limpar_expiradas(db_cadastros)==0
    assert scalar(db_cadastros,'SELECT count(*) FROM mensagens_chat')==2
    assert scalar(db_cadastros,'SELECT count(*) FROM alunos')==2

def test_comprovante_antigo_nao_cancela_entrega_nova(client,db_cadastros):
    assert client.post('/api/itens',headers=SEC,json={'nome':'Livro','descricao':'Livro azul'}).status_code==200
    item=scalar(db_cadastros,'SELECT MAX(id) FROM itens')
    assert client.put(f'/api/itens/{item}',headers=SEC,json={'status':'ENTREGUE'}).status_code==200
    antigo=client.get('/api/entregues',headers=SEC).json[0]['id']
    assert client.put(f'/api/itens/{item}/recusar',headers=SEC,json={'entrega_id':antigo}).status_code==200
    assert client.put(f'/api/itens/{item}',headers=SEC,json={'status':'ENTREGUE'}).status_code==200
    assert client.put(f'/api/itens/{item}/recusar',headers=SEC,json={'entrega_id':antigo}).status_code==409
    assert len(client.get('/api/entregues',headers=SEC).json)==1

def test_reversao_com_falha_faz_rollback(client,db_cadastros):
    assert client.post('/api/itens',headers=SEC,json={'nome':'Livro','descricao':'Livro azul'}).status_code==200
    item=scalar(db_cadastros,'SELECT MAX(id) FROM itens')
    assert client.put(f'/api/itens/{item}',headers=SEC,json={'status':'ENTREGUE'}).status_code==200
    with db_cadastros() as co:
        with co.cursor() as c:
            c.execute("""CREATE FUNCTION falha_teste() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'falha controlada'; END; $$ LANGUAGE plpgsql;
            CREATE TRIGGER teste_falha BEFORE UPDATE ON itens FOR EACH ROW EXECUTE FUNCTION falha_teste();""")
    assert client.put(f'/api/itens/{item}/recusar',headers=SEC).status_code==503
    assert len(client.get('/api/entregues',headers=SEC).json)==1
    assert scalar(db_cadastros,'SELECT status FROM itens WHERE id=%s',(item,))=='ENTREGUE'

def test_limpeza_coordenada_e_repetivel(client,db_cadastros):
    with db_cadastros() as co:
        with co.cursor() as c:c.execute("INSERT INTO mensagens_chat (rm_aluno,nome_aluno,remetente,mensagem,data_envio,criada_em) VALUES ('12345','Aluno','ALUNO','antiga','data antiga',CURRENT_TIMESTAMP-INTERVAL '31 days')")
    lock=db_cadastros();c=lock.cursor();c.execute('SELECT pg_advisory_xact_lock(281030001)')
    try:assert limpar_expiradas(db_cadastros)==0
    finally:lock.rollback();lock.close()
    assert limpar_expiradas(db_cadastros)==1
    assert limpar_expiradas(db_cadastros)==0
