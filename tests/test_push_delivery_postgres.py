"""Integração opcional com PostgreSQL temporário: pip install pgserver.
Não acessa o banco configurado no ambiente nem um provedor push externo.
"""
import json
import os
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest
from psycopg2 import sql
from requests import Response

pgserver=pytest.importorskip('pgserver')
import server
import database
from blueprints import chat,itens
from services import push_delivery as service,push_service
from tests.test_push_delivery import configured,subscription


@pytest.fixture(scope='module')
def postgres(tmp_path_factory):
    runtime=tmp_path_factory.mktemp('push-runtime');os.environ.setdefault('XDG_RUNTIME_DIR',str(runtime))
    pg=pgserver.get_server(tmp_path_factory.mktemp('push-postgres'),cleanup_mode='delete')
    yield pg.get_uri()
    pg.cleanup()


@pytest.fixture
def db_env(postgres,configured,monkeypatch):
    schema='push_'+uuid.uuid4().hex
    with psycopg2.connect(postgres) as connection:
        with connection.cursor() as c:c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    def connect():return psycopg2.connect(postgres,options='-c search_path='+schema)
    for module in [server,database,chat,itens,service,push_service]:
        monkeypatch.setattr(module,'get_db_connection',connect)
    monkeypatch.setattr(server,'DATABASE_URL','banco-temporario')
    monkeypatch.setattr(database,'DATABASE_URL','banco-temporario')
    monkeypatch.setattr(service,'acordar_worker',lambda:None)
    server.limiter.enabled=False
    server.init_db();database.init_db();server.init_db()
    with connect() as connection:
        with connection.cursor() as c:
            for email in ['a@aluno.cps.sp.gov.br','b@aluno.cps.sp.gov.br']:
                c.execute('INSERT INTO alunos (email,nome,rm,senha_hash) VALUES (%s,%s,%s,%s)',(email,'Aluno','12345','hash-nao-usado'))
    yield connect
    with psycopg2.connect(postgres) as connection:
        with connection.cursor() as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def scalar(connect,query,params=()):
    with connect() as connection:
        with connection.cursor() as c:c.execute(query,params);return c.fetchone()[0]


def register(email='a@aluno.cps.sp.gov.br'):
    sub,_,_=subscription();sub['endpoint']+='/'+uuid.uuid4().hex;push_service.salvar_assinatura(email,sub);return sub


def test_fila_persistida_cifrada_e_multiplos_dispositivos(db_env):
    register();register();register('b@aluno.cps.sp.gov.br')
    assert service.enfileirar('a@aluno.cps.sp.gov.br','item',iniciar=False)==2
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==2
    sent=[]
    def transport(self,request,**kwargs):
        sent.append(request.body);r=Response();r.status_code=201;r._content=b'';return r
    with patch('requests.sessions.Session.send',transport):assert service.processar_pendentes()==2
    assert len(sent)==2
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==0
    assert scalar(db_env,'SELECT count(*) FROM push_dispositivos')==3


@pytest.mark.parametrize('status',[404,410])
def test_expiracao_remove_apenas_dispositivo_correspondente(db_env,status):
    register();register('b@aluno.cps.sp.gov.br')
    service.enfileirar('a@aluno.cps.sp.gov.br','chat',iniciar=False)
    r=Response();r.status_code=status;r._content=b''
    with patch('requests.sessions.Session.send',return_value=r):assert service.processar_pendentes()==1
    assert scalar(db_env,'SELECT count(*) FROM push_dispositivos')==1
    assert scalar(db_env,'SELECT email_aluno FROM push_dispositivos')=='b@aluno.cps.sp.gov.br'


def test_retry_tem_limite_e_nao_remove_assinatura_por_falha_temporaria(db_env):
    register();service.enfileirar('a@aluno.cps.sp.gov.br','chat',iniciar=False)
    r=Response();r.status_code=503;r._content=b''
    with patch('requests.sessions.Session.send',return_value=r):
        assert service.processar_pendentes()==1
        assert scalar(db_env,'SELECT tentativas FROM push_entregas')==1
        assert service.processar_pendentes()==0
        for _ in range(3):
            with db_env() as connection:
                with connection.cursor() as c:c.execute("UPDATE push_entregas SET proxima_tentativa=CURRENT_TIMESTAMP - INTERVAL '1 second'")
            assert service.processar_pendentes()==1
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==0
    assert scalar(db_env,'SELECT count(*) FROM push_dispositivos')==1


def test_fila_verifica_revinculacao_antes_de_enviar(db_env):
    sub=register();service.enfileirar('a@aluno.cps.sp.gov.br','chat',iniciar=False)
    push_service.salvar_assinatura('b@aluno.cps.sp.gov.br',sub)
    with patch('requests.sessions.Session.send') as transport:
        assert service.processar_pendentes()==1;transport.assert_not_called()
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==0


def test_claim_e_exclusivo_e_retoma_trabalho_apos_expirar_reserva(db_env):
    register();service.enfileirar('a@aluno.cps.sp.gov.br','chat',iniciar=False)
    first=service._proxima();assert first is not None
    assert service._proxima() is None
    with db_env() as connection:
        with connection.cursor() as c:c.execute("UPDATE push_entregas SET reservado_ate=CURRENT_TIMESTAMP - INTERVAL '1 second'")
    resumed=service._proxima();assert resumed['id']==first['id'] and resumed['tentativas']==2


def test_cooldown_de_teste_e_conta_sem_dispositivo(db_env):
    assert service.enfileirar_teste('a@aluno.cps.sp.gov.br')=='sem_dispositivo'
    register()
    assert service.enfileirar_teste('a@aluno.cps.sp.gov.br')=='enfileirado'
    assert service.enfileirar_teste('a@aluno.cps.sp.gov.br')=='limite'
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==1


@pytest.mark.parametrize('implementation',['unificado','modular'])
def test_eventos_reais_de_chat_e_status_enfileiram_para_email_correto(db_env,implementation):
    app=server.app
    if implementation=='modular':
        from flask import Flask
        from blueprints.auth import auth_bp
        app=Flask(__name__);app.register_blueprint(auth_bp);app.register_blueprint(chat.chat_bp);app.register_blueprint(itens.itens_bp)
    app.config['PUSH_AUTOSTART']=False
    client=app.test_client();register()
    student={'Authorization':'Bearer '+server.gerar_token_aluno('a@aluno.cps.sp.gov.br','Aluno A','12345')}
    owner={'Authorization':'Bearer '+server.gerar_token_secretaria('secretaria@etec.sp.gov.br')}
    assert client.post('/api/chat/enviar',headers=student,json={'mensagem':'conteudo privado','email':'b@aluno.cps.sp.gov.br'}).status_code==200
    assert client.post('/api/chat/enviar',headers=owner,json={'rm':'12345','email':'a@aluno.cps.sp.gov.br','mensagem':'resposta privada'}).status_code==200
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==1
    payload=scalar(db_env,'SELECT payload_json FROM push_entregas')
    assert 'privado' not in payload and 'privada' not in payload
    with db_env() as connection:
        with connection.cursor() as c:
            c.execute("INSERT INTO itens (id,nome_item,descricao,categoria,data_encontrado,local_encontrado,status,aprovado,email_solicitante,solicitado_por,rm_aluno) VALUES (7,'Estojo','Estojo','OUTROS','06/11/2026','Pátio','SOLICITADO',TRUE,'a@aluno.cps.sp.gov.br','Aluno A','12345')")
    response=client.put('/api/itens/7',headers=owner,json={'status':'ENTREGUE'})
    assert response.status_code==200,response.json
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==2
    assert client.put('/api/itens/7',headers=owner,json={'status':'ENTREGUE'}).status_code==200
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==2


def test_410_durante_troca_de_conta_nao_remove_vinculo_novo(db_env):
    sub=register();service.enfileirar('a@aluno.cps.sp.gov.br','chat',iniciar=False)
    def transport(self,request,**kwargs):
        push_service.salvar_assinatura('b@aluno.cps.sp.gov.br',sub)
        r=Response();r.status_code=410;r._content=b'';return r
    with patch('requests.sessions.Session.send',transport):assert service.processar_pendentes()==1
    assert scalar(db_env,'SELECT email_aluno FROM push_dispositivos')=='b@aluno.cps.sp.gov.br'


@pytest.mark.parametrize('implementation',['unificado','modular'])
def test_match_mural_e_recusa_geram_avisos_genericos_apos_commit(db_env,implementation):
    app=server.app
    if implementation=='modular':
        from flask import Flask
        app=Flask(__name__);app.register_blueprint(itens.itens_bp)
    app.config['PUSH_AUTOSTART']=False
    owner={'Authorization':'Bearer '+server.gerar_token_secretaria('secretaria@etec.sp.gov.br')}
    register()
    with db_env() as connection:
        with connection.cursor() as c:
            for _ in range(2):
                c.execute("INSERT INTO mural_perdidos (nome_aluno,rm_aluno,email_aluno,categoria,descricao,data_registro,status) VALUES ('Aluno A','12345','a@aluno.cps.sp.gov.br','OUTROS','Perdi estojo preto','06/11/2026','PROCURANDO')")
    with patch.object(server,'disparar_email'),patch.object(itens,'disparar_email'):
        result=app.test_client().post('/api/itens',headers=owner,json={'nome':'Estojo preto','descricao':'estojo preto','categoria':'OUTROS','fotos':[]})
    assert result.status_code==200,result.json
    from services.matches_service import processar
    processar(db_env)
    # Dois relatos da mesma conta produzem um único aviso por dispositivo.
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==1
    assert 'Estojo' not in scalar(db_env,'SELECT payload_json FROM push_entregas')
    with db_env() as connection:
        with connection.cursor() as c:c.execute("UPDATE itens SET status='SOLICITADO',email_solicitante='a@aluno.cps.sp.gov.br' WHERE id=%s",(result.json['id'],))
    assert app.test_client().put('/api/itens/'+str(result.json['id'])+'/recusar',headers=owner).status_code==200
    assert scalar(db_env,'SELECT count(*) FROM push_entregas')==2


def test_falha_de_fila_nao_desfaz_resposta_do_chat_gravada(db_env):
    register()
    owner={'Authorization':'Bearer '+server.gerar_token_secretaria('secretaria@etec.sp.gov.br')}
    with db_env() as connection:
        with connection.cursor() as c:c.execute("INSERT INTO mensagens_chat(rm_aluno,nome_aluno,remetente,mensagem,data_envio,email_aluno) VALUES ('12345','Aluno A','ALUNO','Oi','06/11/2026','a@aluno.cps.sp.gov.br')")
    with patch.object(service,'enfileirar',side_effect=RuntimeError('fila indisponível')):
        result=server.app.test_client().post('/api/chat/enviar',headers=owner,json={'rm':'12345','email':'a@aluno.cps.sp.gov.br','mensagem':'Resposta'})
    assert result.status_code==200
    assert scalar(db_env,"SELECT count(*) FROM mensagens_chat WHERE remetente='SECRETARIA'")==1
