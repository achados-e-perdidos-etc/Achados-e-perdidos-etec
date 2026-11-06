"""Jornadas integradas com banco PostgreSQL temporário e sem serviços externos."""
from concurrent.futures import ThreadPoolExecutor
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_portal_updates_postgres import db,db_cadastros,auth
from werkzeug.security import generate_password_hash
import server


def test_jornada_aluno_secretaria_com_login_real_e_entrega(db_cadastros):
    client=server.app.test_client()
    with db_cadastros() as co:
        with co.cursor() as c:c.execute('UPDATE alunos SET senha_hash=%s WHERE email=%s',(generate_password_hash('Senha-de-teste-123!'),'a@aluno.cps.sp.gov.br'))
    assert client.post('/api/auth/login-aluno',json={'email':'a@aluno.cps.sp.gov.br','senha':'errada'}).status_code==401
    login=client.post('/api/auth/login-aluno',json={'email':'a@aluno.cps.sp.gov.br','senha':'Senha-de-teste-123!'});assert login.status_code==200
    aluno={'Authorization':'Bearer '+login.json['token']}
    sec={'Authorization':'Bearer '+server.gerar_token_secretaria('sec@etec.sp.gov.br')}
    assert client.post('/api/mural',headers=aluno,json={'categoria':'OUTROS','descricao':'Perdi estojo azul'}).status_code==200
    assert client.post('/api/itens/cadastrar-aluno',headers=auth('b@aluno.cps.sp.gov.br'),json={'nome':'Estojo azul','descricao':'Encontrado no pátio'}).status_code==200
    item=scalar(db_cadastros,'SELECT MAX(id) FROM itens')
    assert not any(i['id']==item for i in client.get('/api/itens').json)
    assert client.put(f'/api/itens/{item}/aprovar',headers=aluno).status_code==403
    assert client.put(f'/api/itens/{item}/aprovar',headers=sec).status_code==200
    assert client.post('/api/solicitar',headers=aluno,json={'id':item}).status_code==200
    assert client.post('/api/chat/enviar',headers=aluno,json={'mensagem':'Vou buscar o estojo'}).status_code==200
    assert client.post('/api/chat/enviar',headers=sec,json={'rm':'12345','mensagem':'Pode vir com documento'}).status_code==200
    assert client.put(f'/api/itens/{item}',headers=sec,json={'status':'ENTREGUE','retirado_por':'Aluno','rm_retirante':'12345'}).status_code==200
    assert client.get('/api/entregues',headers=sec).json[0]['item_id']==item
    assert client.get('/api/itens/meus',headers=aluno).json[0]['status']=='ENTREGUE'
    assert client.get('/api/itens/cadastrados-por-mim',headers=auth('b@aluno.cps.sp.gov.br')).json['cadastros'][0]['situacao']=='ENTREGUE'
    assert client.get('/api/notificacoes',headers=aluno).json['nao_lidas']>=2


def test_duas_solicitacoes_simultaneas_nao_reservam_mesmo_item(db_cadastros):
    with db_cadastros() as co:
        with co.cursor() as c:
            c.execute("INSERT INTO itens (nome_item,descricao,categoria,data_encontrado,local_encontrado) VALUES ('Livro','Livro','OUTROS','06/11/2026','Sala') RETURNING id")
            item=c.fetchone()[0]
    def solicitar(email):
        with server.app.test_client() as client:return client.post('/api/solicitar',headers=auth(email),json={'id':item}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(solicitar,['a@aluno.cps.sp.gov.br','b@aluno.cps.sp.gov.br']))
    assert sorted(statuses)==[200,400]
