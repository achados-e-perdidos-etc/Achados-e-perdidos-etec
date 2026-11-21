"""Catálogo e decisões reais em PostgreSQL temporário, sem dados de produção."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import pytest
import server
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from blueprints import cadastros

ADMIN=auth('secretaria@etec.sp.gov.br',True)

@pytest.fixture
def ambiente(db,monkeypatch):
    monkeypatch.setattr(cadastros,'get_db_connection',db)
    server.app.config['PUSH_AUTOSTART']=False
    return db,server.app.test_client()


def inserir(db,nome='Calculadora científica Casio',categoria='ELETRÔNICOS',data='06/11/2026',local='Pátio',aprovado=True,autor=None):
    with db() as co:
        with co.cursor() as c:
            c.execute('''INSERT INTO itens(nome_item,descricao,categoria,data_encontrado,local_encontrado,status,
             aprovado,email_cadastrador,foto,fotos_json,email_solicitante)
             VALUES(%s,%s,%s,%s,%s,'DISPONÍVEL',%s,%s,%s,%s,'privado@aluno.cps.sp.gov.br') RETURNING id''',
             (nome,'Descrição '+nome,categoria,data,local,aprovado,autor,'https://res.cloudinary.com/teste/image/upload/v1/foto.jpg',json.dumps(['https://res.cloudinary.com/teste/image/upload/v1/foto.jpg'])))
            return c.fetchone()[0]


def test_paginas_pequenas_sem_dados_pessoais_e_sem_repetir_com_novos_itens(ambiente):
    db,client=ambiente
    ids=[inserir(db,nome='Objeto '+str(i)) for i in range(55)]
    inserir(db,nome='Privado',aprovado=False,autor='a@aluno.cps.sp.gov.br')
    r=client.get('/api/catalogo');assert r.status_code==200,r.json
    first=r.json;assert len(first['itens'])==24 and first['tem_mais']
    assert first['teto']==ids[-1]
    assert 'w_480' in first['itens'][0]['miniatura']
    for row in first['itens']:
        assert not {'email_cadastrador','email_solicitante','solicitado_por','rm_aluno','motivo_recusa','recusado_em','fotos_json'}&row.keys()
    novo=inserir(db,nome='Novo após primeira página')
    rows=first['itens'];page=first
    while page['tem_mais']:
        page=client.get('/api/catalogo',query_string={'antes':page['proximo'],'teto':first['teto']}).json
        rows+=page['itens']
    assert [r['id'] for r in rows]==list(reversed(ids))
    assert novo not in [r['id'] for r in rows]
    assert client.get('/api/catalogo').json['itens'][0]['id']==novo


def test_busca_sem_acentos_combina_categoria_local_e_periodo(ambiente):
    db,client=ambiente
    wanted=inserir(db)
    inserir(db,data='01/10/2026');inserir(db,local='Biblioteca');inserir(db,categoria='OUTROS')
    inserir(db,data='31/02/2026');inserir(db,data='legado inválido')
    r=client.get('/api/catalogo',query_string={'q':'calculadora CIENTIFICA','categoria':'eletronicos','local':'patio','inicio':'2026-11-01','fim':'2026-11-07'})
    assert r.status_code==200,r.json
    assert [i['id'] for i in r.json['itens']]==[wanted]
    assert scalar(db,"SELECT etec_normalizar('Óculos AÇÃO çÃÉ')")=='oculos acao cae'
    assert scalar(db,"SELECT etec_data('2026-11-06')")==date(2026,11,6)
    assert scalar(db,"SELECT etec_data('31/02/2026')") is None
    assert len(client.get('/api/catalogo',query_string={'q':'%'}).json['itens'])==0


@pytest.mark.parametrize('query',[{'limite':0},{'limite':49},{'antes':-1},{'teto':'x'},{'antes':'9999999999999999'},{'inicio':'31/02/2026'},{'fim':'2026-02-31'},{'inicio':'2026-11-07','fim':'2026-11-01'},{'status':'x'},{'q':'x'*121}])
def test_filtros_invalidos_rejeitados(ambiente,query):
    _,client=ambiente
    assert client.get('/api/catalogo',query_string=query).status_code==400


def test_recusa_correcao_mesmo_id_privacidade_versao_e_historico_completo(ambiente):
    db,client=ambiente
    id=inserir(db,aprovado=False,autor='a@aluno.cps.sp.gov.br')
    assert client.get(f'/api/catalogo/{id}').status_code==404
    assert client.get('/api/moderacao/cadastros',headers=auth()).status_code==403
    row=client.get('/api/moderacao/cadastros',headers=ADMIN).json['cadastros'][0]
    assert row['id']==id and row['versao']==1
    assert client.put(f'/api/itens/{id}/recusar',headers=ADMIN,json={'versao':1,'motivo':'x'}).status_code==400
    assert scalar(db,'SELECT recusado_em FROM itens WHERE id=%s',(id,)) is None
    reason='Informe o laboratório correto e o estado do objeto.'
    assert client.put(f'/api/itens/{id}/recusar',headers=ADMIN,json={'versao':1,'motivo':reason}).status_code==200
    assert client.get('/api/moderacao/cadastros',headers=ADMIN).json['cadastros']==[]
    refused=client.get('/api/moderacao/cadastros?estado=RECUSADO',headers=ADMIN).json['cadastros'][0]
    assert refused['versao']==2
    personal=client.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]
    assert personal['situacao']=='RECUSADO' and personal['motivo_recusa']==reason and personal['item_id']==id
    assert client.get(f'/api/meus-cadastros/{id}',headers=auth('b@aluno.cps.sp.gov.br')).status_code==404
    assert client.put(f'/api/meus-cadastros/{id}',headers=auth('b@aluno.cps.sp.gov.br'),json={'versao':2}).status_code==404
    assert client.put(f'/api/meus-cadastros/{id}',headers=auth(),json={'versao':1}).status_code==409
    correction={'versao':2,'nome':'Calculadora científica Casio azul','local':'Laboratório 3','descricao':'Calculadora azul com tampa e marca na lateral.'}
    r=client.put(f'/api/meus-cadastros/{id}',headers=auth(),json=correction);assert r.status_code==200,r.json
    assert scalar(db,'SELECT count(*) FROM itens')==1
    assert scalar(db,'SELECT fotos_json FROM itens WHERE id=%s',(id,))==json.dumps(['https://res.cloudinary.com/teste/image/upload/v1/foto.jpg'])
    assert client.get('/api/itens/cadastrados-por-mim',headers=auth()).json['cadastros'][0]['situacao']=='AGUARDANDO'
    assert client.put(f'/api/itens/{id}/aprovar',headers=ADMIN,json={'versao':2}).status_code==409
    assert client.put(f'/api/itens/{id}/aprovar',headers=ADMIN,json={'versao':3}).status_code==200
    assert client.get(f'/api/catalogo/{id}').json['item']['txt_local']=='Laboratório 3'
    assert client.put(f'/api/meus-cadastros/{id}',headers=auth(),json={'versao':4}).status_code==409
    logs=client.get(f'/api/itens/{id}/ocorrencias',headers=ADMIN).json['ocorrencias']
    assert logs[0]['ator_id']=='secretaria@etec.sp.gov.br'
    edit=next(row for row in logs if row['ator_id']=='a@aluno.cps.sp.gov.br')
    assert any(c['chave']=='local' and c['antes']=='Pátio' and c['depois']=='Laboratório 3' for c in edit['alteracoes'])
    assert any(c['chave']=='descricao' for c in edit['alteracoes'])
    assert any(c['chave']=='motivo_recusa' and c['depois']==reason for row in logs for c in row['alteracoes'])
    assert client.get(f'/api/itens/{id}/ocorrencias',headers=auth()).status_code==403


def test_decisoes_simultaneas_exigem_versao_atual_e_liberam_locks(ambiente):
    db,_=ambiente;id=inserir(db,aprovado=False,autor='a@aluno.cps.sp.gov.br')
    def decidir(_):
        return server.app.test_client().put(f'/api/itens/{id}/aprovar',headers=ADMIN,json={'versao':1}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(decidir,range(2)))
    assert sorted(codes)==[200,409]
    assert scalar(db,'SELECT versao FROM itens WHERE id=%s',(id,))==2


def test_duplicidade_sugerida_sem_ia_e_confirmacao_explicita_auditada(ambiente):
    db,client=ambiente
    match=inserir(db,nome='Óculos de grau preto',categoria='ACESSÓRIOS')
    inserir(db,nome='Óculos de grau preto',categoria='OUTROS')
    inserir(db,nome='Óculos de grau preto',categoria='ACESSÓRIOS',data='01/09/2026')
    payload={'nome':'Oculos de grau preto','descricao':'Óculos pretos','categoria':'ACESSÓRIOS','data':'06/11/2026','local':'Pátio','fotos':[]}
    assert client.post('/api/itens/duplicados',headers=auth(),json=payload).status_code==403
    response=client.post('/api/itens/duplicados',headers=ADMIN,json=payload)
    assert response.status_code==200,response.json
    assert [r['id'] for r in response.json['duplicados']]==[match]
    before=scalar(db,'SELECT count(*) FROM itens')
    r=client.post('/api/itens',headers=ADMIN,json=payload)
    assert r.status_code==409 and r.json['code']=='POSSIVEL_DUPLICADO'
    assert scalar(db,'SELECT count(*) FROM itens')==before
    payload['confirmar_duplicado']=True
    r=client.post('/api/itens',headers=ADMIN,json=payload);assert r.status_code==200,r.json
    id=r.json['id'];assert id!=match
    assert scalar(db,"SELECT ator_id FROM ocorrencias_itens WHERE item_id=%s AND acao='REV_DUPLIC'",(id,))=='secretaria@etec.sp.gov.br'
    pending=inserir(db,nome='Óculos de grau preto',categoria='ACESSÓRIOS',aprovado=False,autor='a@aluno.cps.sp.gov.br')
    assert client.put(f'/api/itens/{pending}/aprovar',headers=ADMIN,json={'versao':1}).status_code==409
    assert scalar(db,'SELECT aprovado FROM itens WHERE id=%s',(pending,)) is False
    assert client.put(f'/api/itens/{pending}/aprovar',headers=ADMIN,json={'versao':1,'confirmar_duplicado':True}).status_code==200
