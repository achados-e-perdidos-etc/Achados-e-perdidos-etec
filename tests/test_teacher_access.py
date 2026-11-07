"""Contratos de aprovação: rotas Flask reais e SQL do serviço em banco isolado."""
import sqlite3
from unittest.mock import MagicMock, patch
import pytest
import server
from services import professores_service as service
from utils.professores import SCHEMA_ACESSO_PROFESSORES

class Cursor:
    def __init__(self, db):
        self.c = db.cursor()
    def execute(self, query, params=()):
        self.c.execute(query.replace('%s', '?'), params)
    def fetchone(self):
        row = self.c.fetchone()
        return dict(row) if row is not None else None
    def fetchall(self):
        return [dict(row) for row in self.c.fetchall()]

class Connection:
    def __init__(self, db): self.db = db
    def cursor(self, **kwargs): return Cursor(self.db)
    def commit(self): self.db.commit()
    def close(self): pass

@pytest.fixture(params=['unificado', 'modular'])
def env(request):
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('CREATE TABLE alunos (email TEXT PRIMARY KEY, nome TEXT NOT NULL)')
    db.executescript(SCHEMA_ACESSO_PROFESSORES)
    for email, nome in [('docente@etec.sp.gov.br', 'Docente real'), ('outro@etec.sp.gov.br','Outro docente')]:
        db.execute('INSERT INTO alunos VALUES (?,?)', (email,nome))
    db.commit()
    app = server.app
    resource_module = server
    if request.param == 'modular':
        from flask import Flask
        from blueprints.auth import auth_bp
        from blueprints import itens
        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        app.register_blueprint(itens.itens_bp)
        resource_module = itens
    app.config['TESTING'] = True
    server.limiter.enabled = False
    admin_db = MagicMock()
    admin_db.cursor.return_value.fetchone.return_value={'id':1,'versao':1,'aprovado':False,'nome_item':'Estojo','descricao':'Estojo preto','categoria':'OUTROS','data_encontrado':'06/11/2026'}
    admin_db.cursor.return_value.fetchall.return_value=[]
    with patch.object(service, 'get_db_connection', return_value=Connection(db)), \
         patch.object(resource_module, 'get_db_connection', return_value=admin_db) as resource:
        yield {'client': app.test_client(), 'db':db, 'resource':resource}
    db.close()

def headers(email='docente@etec.sp.gov.br', role='aluno'):
    token = server.gerar_token_secretaria(email) if role=='secretaria' else server.gerar_token_aluno(email,'Nome do token','PROFESSOR')
    return {'Authorization':'Bearer '+token}

OWNER = {'email':'secretaria@etec.sp.gov.br','role':'secretaria'}
TARGET='/api/secretaria/professores/docente@etec.sp.gov.br/acesso'

def decide(client, action, auth=None):
    return client.put(TARGET, json={'acao':action}, headers=auth or headers(**OWNER))

def test_solicitar_nao_concede_privilegio_e_decisao_exige_secretaria(env):
    c=env['client']
    assert c.get('/api/professores/acesso',headers=headers()).json['status']=='NAO_SOLICITADO'
    result=c.post('/api/professores/acesso',headers=headers(),json={'email':'outro@etec.sp.gov.br','status':'APROVADO','role':'secretaria'})
    assert result.status_code==200 and result.json['status']=='PENDENTE'
    row=env['db'].execute('SELECT * FROM professores_acesso').fetchone()
    assert row['email']=='docente@etec.sp.gov.br' and row['nome']=='Docente real'
    assert c.put('/api/itens/1/aprovar',headers=headers()).status_code==403
    assert decide(c,'APROVAR',headers()).status_code==403
    assert env['resource'].call_count==0
    assert c.post('/api/professores/acesso',headers=headers()).json['status']=='PENDENTE'
    assert env['db'].execute('SELECT COUNT(*) FROM professores_acesso').fetchone()[0]==1

def test_aprovar_libera_mesmo_token_e_revogar_bloqueia_imediatamente(env):
    c=env['client']; auth=headers()
    c.post('/api/professores/acesso',headers=auth)
    assert decide(c,'APROVAR').json['status']=='APROVADO'
    assert c.put('/api/itens/1/aprovar',headers=auth,json={'versao':1}).status_code==200
    env['resource'].reset_mock()
    # Approved professors cannot approve others, even while operating the panel.
    assert c.get('/api/secretaria/professores',headers=auth).status_code==403
    assert decide(c,'REVOGAR',auth).status_code==403
    assert c.post('/api/professores/acesso',headers=auth).json['status']=='APROVADO'
    assert decide(c,'REVOGAR').json['status']=='REVOGADO'
    assert c.put('/api/itens/1/aprovar',headers=auth).status_code==403
    env['resource'].assert_not_called()
    assert c.get('/api/professores/acesso',headers=auth).json['status']=='REVOGADO'

def test_recusa_auditoria_e_nova_solicitacao(env):
    c=env['client']
    c.post('/api/professores/acesso',headers=headers())
    assert decide(c,'RECUSAR').json['status']=='RECUSADO'
    assert c.put('/api/itens/1/aprovar',headers=headers()).status_code==403
    row=env['db'].execute('SELECT * FROM professores_acesso').fetchone()
    assert row['decidido_por']==OWNER['email'] and row['data_decisao']
    assert c.post('/api/professores/acesso',headers=headers()).json['status']=='PENDENTE'
    row=env['db'].execute('SELECT * FROM professores_acesso').fetchone()
    assert row['decidido_por'] is None and row['data_decisao'] is None

def test_aluno_ou_visitante_nao_solicita_nem_decide(env):
    c=env['client']
    for auth, status in [({},401),(headers('aluno@aluno.cps.sp.gov.br'),403)]:
        assert c.post('/api/professores/acesso',headers=auth).status_code==status
        assert c.get('/api/secretaria/professores',headers=auth).status_code==status
        assert c.put(TARGET,headers=auth,json={'acao':'APROVAR'}).status_code==status
    assert env['db'].execute('SELECT COUNT(*) FROM professores_acesso').fetchone()[0]==0

def test_pedido_inexistente_estado_invalido_e_revisao_de_lista(env):
    c=env['client']
    assert decide(c,'APROVAR').status_code==409
    assert decide(c,'OUTRA_ACAO').status_code==400
    c.post('/api/professores/acesso',headers=headers())
    listing=c.get('/api/secretaria/professores',headers=headers(**OWNER))
    assert listing.status_code==200 and listing.json['solicitacoes'][0]['status']=='PENDENTE'
    assert 'no-store' in listing.headers['Cache-Control']
    assert decide(c,'APROVAR').status_code==200
    assert decide(c,'RECUSAR').status_code==409
    assert decide(c,'APROVAR').status_code==409

def test_falha_ao_consultar_permissao_nao_libera_painel(env):
    with patch.object(service,'buscar_acesso',side_effect=RuntimeError('indisponível')):
        response=env['client'].put('/api/itens/1/aprovar',headers=headers())
        assert response.status_code==503
        env['resource'].assert_not_called()

def test_conta_inexistente_nao_cria_pedido(env):
    response=env['client'].post('/api/professores/acesso',headers=headers('inexistente@etec.sp.gov.br'))
    assert response.status_code==403
    assert env['db'].execute('SELECT COUNT(*) FROM professores_acesso').fetchone()[0]==0
