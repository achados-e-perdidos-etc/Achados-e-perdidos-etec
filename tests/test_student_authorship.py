"""Autoria persistida e consultas pessoais com duas sessões e SQL real isolado."""
import sqlite3
from contextlib import ExitStack
from unittest.mock import patch

import pytest
import server


class Cursor:
    def __init__(self, connection):
        self.cursor = connection.cursor()

    def execute(self, query, params=()):
        self.cursor.execute(query.replace('%s', '?'), params)
        # Consome RETURNING antes de commit, como o cursor PostgreSQL permite.
        self.rows = self.cursor.fetchall() if self.cursor.description else []

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchall(self):
        rows, self.rows = self.rows, []
        return [dict(row) for row in rows]

    def fetchone(self):
        row = self.rows.pop(0) if self.rows else None
        return dict(row) if row else None

    def close(self):
        self.cursor.close()


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def cursor(self, **kwargs):
        return Cursor(self.connection)

    def commit(self):
        self.connection.commit()

    def close(self):
        pass  # A conexão pertence ao teste, não a uma requisição.


@pytest.mark.parametrize('implementation', ['unificado', 'modular'])
def test_solicitacao_relato_e_cadastro_ficam_com_o_autor_da_sessao(implementation):
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE itens (
            id INTEGER PRIMARY KEY, nome_item TEXT, descricao TEXT, categoria TEXT,
            data_encontrado TEXT, local_encontrado TEXT, foto TEXT, fotos_json TEXT,
            status TEXT, aprovado BOOLEAN, cadastrado_por_aluno BOOLEAN,
            solicitado_por TEXT, rm_aluno TEXT, email_solicitante TEXT);
        CREATE TABLE mural_perdidos (
            id INTEGER PRIMARY KEY, nome_aluno TEXT, rm_aluno TEXT, email_aluno TEXT,
            categoria TEXT, descricao TEXT, data_registro TEXT, status TEXT);
        INSERT INTO itens (id,nome_item,descricao,categoria,status,aprovado)
            VALUES (7,'Estojo','Estojo preto','OUTROS','DISPONÍVEL',TRUE);
    ''')
    app = server.app
    modules = [server]
    if implementation == 'modular':
        from flask import Flask
        from blueprints import itens, mural
        app = Flask(__name__)
        app.register_blueprint(itens.itens_bp)
        app.register_blueprint(mural.mural_bp)
        modules = [itens, mural]
    app.config['TESTING'] = True
    server.limiter.enabled = False
    try:
        with ExitStack() as stack:
            for module in modules:
                stack.enter_context(patch.object(module, 'get_db_connection', return_value=Connection(db)))
            stack.enter_context(patch('server.processar_fotos', return_value=[]))
            stack.enter_context(patch('blueprints.itens.processar_fotos', return_value=[]))
            client = app.test_client()
            def headers(email, nome, rm):
                return {'Authorization': 'Bearer ' + server.gerar_token_aluno(email, nome, rm)}
            first = headers('primeiro@aluno.cps.sp.gov.br', 'Primeiro aluno', '12345')
            second = headers('segundo@aluno.cps.sp.gov.br', 'Segundo aluno', '99999')
            forged = {'nome': 'Segundo aluno', 'rm': '99999', 'email': 'segundo@aluno.cps.sp.gov.br'}

            response = client.post('/api/solicitar', headers=first, json={'id': 7, **forged})
            assert response.status_code == 200, response.json
            row = dict(db.execute('SELECT * FROM itens WHERE id=7').fetchone())
            assert (row['solicitado_por'], row['rm_aluno'], row['email_solicitante']) == (
                'Primeiro aluno', '12345', 'primeiro@aluno.cps.sp.gov.br')
            assert client.get('/api/itens/meus', headers=first).json[0]['id'] == 7
            assert client.get('/api/itens/meus', headers=second).json == []
            # Outro aluno não consegue substituir uma solicitação existente.
            assert client.post('/api/solicitar', headers=second, json={'id': 7}).status_code == 400

            response = client.post('/api/mural', headers=first, json={
                **forged, 'categoria': 'OUTROS', 'descricao': 'Perdi minha garrafa'})
            assert response.status_code == 200
            row = dict(db.execute('SELECT * FROM mural_perdidos').fetchone())
            assert (row['nome_aluno'], row['rm_aluno'], row['email_aluno']) == (
                'Primeiro aluno', '12345', 'primeiro@aluno.cps.sp.gov.br')
            assert len(client.get('/api/mural/aluno/12345', headers=first).json) == 1
            assert client.get('/api/mural/aluno/99999', headers=second).json == []
            assert client.get('/api/mural/aluno/12345', headers=second).status_code == 403

            response = client.post('/api/itens/cadastrar-aluno', headers=first, json={
                'nome': 'Controle branco', 'descricao': 'Objeto encontrado', 'rm': '99999'})
            assert response.status_code == 200
            row = dict(db.execute('SELECT * FROM itens WHERE id != 7').fetchone())
            assert row['nome_item'] == 'Controle branco'
            assert row['rm_aluno'] == '12345'
            assert not row['aprovado']
            assert row['cadastrado_por_aluno']
            # Adivinhar o ID não permite solicitar um objeto ainda em moderação.
            assert client.post('/api/solicitar', headers=second, json={'id': row['id']}).status_code == 400
            assert db.execute('SELECT status FROM itens WHERE id=?', (row['id'],)).fetchone()[0] == 'DISPONÍVEL'
    finally:
        db.close()
