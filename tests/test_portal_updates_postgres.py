"""Fluxos reais isolados: avisos e autoria. Nunca usa o banco da hospedagem."""
import pytest
from unittest.mock import patch
from tests.test_push_delivery_postgres import postgres, db_env, scalar
from tests.test_push_delivery import configured
from services import notificacoes_service, push_delivery
from blueprints import notificacoes
import server

@pytest.fixture
def db(db_env, monkeypatch):
    for mod in [notificacoes_service, notificacoes]:monkeypatch.setattr(mod,'get_db_connection',db_env)
    return db_env

def auth(email='a@aluno.cps.sp.gov.br'):
    return {'Authorization':'Bearer '+server.gerar_token_aluno(email,'Aluno','12345')}

def test_central_sem_push_e_separada_por_conta(db,monkeypatch):
    monkeypatch.setattr(push_delivery,'configuracao',lambda:None)
    push_delivery.notificar('a@aluno.cps.sp.gov.br','item')
    push_delivery.notificar('b@aluno.cps.sp.gov.br','chat')
    client=server.app.test_client()
    assert client.get('/api/notificacoes').status_code==401
    res=client.get('/api/notificacoes',headers=auth());assert res.status_code==200
    data=res.json;assert data['nao_lidas']==1 and len(data['notificacoes'])==1
    own=data['notificacoes'][0]['id']
    other=client.get('/api/notificacoes',headers=auth('b@aluno.cps.sp.gov.br')).json['notificacoes'][0]['id']
    assert client.put(f'/api/notificacoes/{other}/lida',headers=auth()).status_code==404
    assert client.put(f'/api/notificacoes/{own}/lida',headers=auth()).status_code==200
    assert client.get('/api/notificacoes',headers=auth()).json['nao_lidas']==0
    assert client.get('/api/notificacoes',headers=auth('b@aluno.cps.sp.gov.br')).json['nao_lidas']==1

def test_paginacao_e_leitura_preserva_avisos_novos(db):
    for _ in range(33):notificacoes_service.registrar('a@aluno.cps.sp.gov.br','item')
    client=server.app.test_client();data=client.get('/api/notificacoes',headers=auth()).json
    assert len(data['notificacoes'])==30 and data['tem_mais']
    ids=[n['id'] for n in data['notificacoes']]
    next_page=client.get('/api/notificacoes?antes='+str(ids[-1]),headers=auth()).json
    assert len(next_page['notificacoes'])==3 and not next_page['tem_mais']
    assert not set(ids).intersection(n['id'] for n in next_page['notificacoes'])
    notificacoes_service.registrar('a@aluno.cps.sp.gov.br','chat')
    assert client.put('/api/notificacoes/lidas',headers=auth(),json={'ate_id':ids[0]}).status_code==200
    assert client.get('/api/notificacoes',headers=auth()).json['nao_lidas']==1
    for value in ['', 'abc','-1','999999999999999999999']:
        assert client.get('/api/notificacoes?antes='+value,headers=auth()).status_code==400
    assert client.put('/api/notificacoes/lidas',headers=auth(),json={'ate_id':True}).status_code==400

def test_resposta_chat_registra_sem_configurar_push(db,monkeypatch):
    monkeypatch.setattr(push_delivery,'configuracao',lambda:None)
    client=server.app.test_client()
    assert client.post('/api/chat/enviar',headers=auth(),json={'mensagem':'Olá'}).status_code==200
    sec={'Authorization':'Bearer '+server.gerar_token_secretaria('sec@etec.sp.gov.br')}
    assert client.post('/api/chat/enviar',headers=sec,json={'rm':'12345','email':'a@aluno.cps.sp.gov.br','mensagem':'Bom dia!'}).status_code==200
    assert client.get('/api/notificacoes',headers=auth()).json['nao_lidas']==1

@pytest.fixture
def db_cadastros(db,monkeypatch):
    from blueprints import cadastros
    monkeypatch.setattr(cadastros,'get_db_connection',db)
    return db

@pytest.mark.parametrize('modular',[False,True])
def test_cadastros_seguem_autor_e_preservam_recusa(db_cadastros,modular):
    from flask import Flask
    from blueprints.itens import itens_bp
    app=Flask(__name__) if modular else server.app
    if modular:app.register_blueprint(itens_bp)
    client=app.test_client();owner=server.app.test_client()
    sec={'Authorization':'Bearer '+server.gerar_token_secretaria('sec@etec.sp.gov.br')}
    payload={'nome':'Mochila','descricao':'Mochila preta','categoria':'MOCHILA','email':'b@aluno.cps.sp.gov.br'}
    assert client.post('/api/itens/cadastrar-aluno',headers=auth(),json=payload).status_code==200
    data=owner.get('/api/itens/cadastrados-por-mim',headers=auth()).json
    assert data['cadastros'][0]['situacao']=='AGUARDANDO'
    assert owner.get('/api/itens/cadastrados-por-mim',headers=auth('b@aluno.cps.sp.gov.br')).json['cadastros']==[]
    item_id=scalar(db_cadastros,'SELECT id FROM itens ORDER BY id DESC LIMIT 1')
    assert client.put(f'/api/itens/{item_id}/aprovar',headers=sec,json={'versao':1}).status_code==200
    assert owner.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']=='PUBLICADO'
    assert client.post('/api/solicitar',headers=auth('b@aluno.cps.sp.gov.br'),json={'id':item_id}).status_code==200
    assert owner.get('/api/itens/cadastrados-por-mim',headers=auth('b@aluno.cps.sp.gov.br')).json['cadastros']==[]
    assert client.put(f'/api/itens/{item_id}',headers=sec,json={'status':'ENTREGUE'}).status_code==200
    assert owner.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']=='ENTREGUE'
    assert client.post('/api/itens/cadastrar-aluno',headers=auth(),json=payload).status_code==200
    rejected=scalar(db_cadastros,'SELECT id FROM itens ORDER BY id DESC LIMIT 1')
    assert client.put(f'/api/itens/{rejected}/recusar',headers=sec,json={'versao':1,'motivo':'Informe o local encontrado.'}).status_code==200
    assert owner.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']=='RECUSADO'
    assert scalar(db_cadastros,'SELECT count(*) FROM itens WHERE id=%s',(rejected,))==1
    assert scalar(db_cadastros,'SELECT motivo_recusa FROM itens WHERE id=%s',(rejected,))=='Informe o local encontrado.'
    assert owner.get('/api/itens/cadastrados-por-mim').status_code==401

def test_doacao_e_remocao_preservam_historico_sem_expor_autoria(db_cadastros):
    client=server.app.test_client();sec={'Authorization':'Bearer '+server.gerar_token_secretaria('sec@etec.sp.gov.br')}
    assert client.post('/api/itens/cadastrar-aluno',headers=auth(),json={'nome':'Estojo','descricao':'Estojo azul'}).status_code==200
    item=scalar(db_cadastros,'SELECT MAX(id) FROM itens')
    assert client.put(f'/api/itens/{item}/aprovar',headers=sec,json={'versao':1}).status_code==200
    for status,situacao in [('PARA DOAÇÃO','PARA DOAÇÃO'),('DOAÇÃO FEITA','DOADO')]:
        assert client.put(f'/api/itens/{item}',headers=sec,json={'status':status}).status_code==200
        assert client.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']==situacao
    for row in client.get('/api/itens').json:
        assert 'email_cadastrador' not in row and 'email_aluno' not in row
    assert client.delete(f'/api/itens/{item}',headers=sec).status_code==200
    assert client.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']=='REMOVIDO'

def test_professor_aprovado_ve_somente_proprios_cadastros(db_cadastros,monkeypatch):
    from services import professores_service
    monkeypatch.setattr(professores_service,'get_db_connection',db_cadastros)
    email='professor@etec.sp.gov.br'
    with db_cadastros() as co:
        with co.cursor() as cu:
            cu.execute('INSERT INTO alunos VALUES (%s,%s,%s,%s)',(email,'Docente','PROFESSOR','hash-nao-usado'))
            cu.execute("INSERT INTO professores_acesso (email,nome,status) VALUES (%s,%s,'APROVADO')",(email,'Docente'))
    professor={'Authorization':'Bearer '+server.gerar_token_aluno(email,'Docente','PROFESSOR')}
    client=server.app.test_client()
    assert client.post('/api/itens/cadastrar-aluno',headers=professor,json={'nome':'Fone','descricao':'Encontrado'}).status_code==200
    assert len(client.get('/api/itens/cadastrados-por-mim',headers=professor).json['cadastros'])==1
    assert client.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros']==[]
