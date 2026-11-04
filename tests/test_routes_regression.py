"""Regressões das rotas reais sem acesso a banco ou integrações externas.

Execute com DATABASE_URL vazio e JWT_SECRET de teste definido no ambiente.
"""
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

import server
from utils.helpers import validar_email_institucional


class RouteTests(unittest.TestCase):
    def setUp(self):
        server.app.config['TESTING'] = True
        server.limiter.enabled = False
        self.client = server.app.test_client()
        self.aluno = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
            'aluno@aluno.cps.sp.gov.br', 'Nome real', '12345')}
        self.secretaria = {'Authorization': 'Bearer ' + server.gerar_token_secretaria(
            'secretaria@etec.sp.gov.br')}
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchall.return_value = []
        self.db_patch = patch.object(server, 'get_db_connection', return_value=self.connection)
        self.get_db = self.db_patch.start()
        self.addCleanup(self.db_patch.stop)

    def test_rotas_administrativas_rejeitam_visitantes_e_alunos(self):
        routes = [
            ('GET', '/api/itens/pendentes'), ('PUT', '/api/itens/1/aprovar'),
            ('POST', '/api/itens'), ('PUT', '/api/itens/1'),
            ('POST', '/api/itens/1'), ('DELETE', '/api/itens/1'),
            ('PUT', '/api/itens/1/recusar'), ('DELETE', '/api/itens/doacoes/concluir'),
            ('DELETE', '/api/mural/1'), ('GET', '/api/chat/conversas'),
            ('GET', '/api/entregues'), ('GET', '/api/estatisticas'),
            ('GET', '/api/smart-match'), ('POST', '/api/categorias'),
            ('DELETE', '/api/categorias'), ('DELETE', '/api/categorias/OUTROS'),
        ]
        for method, path in routes:
            for headers, status in [({}, 401), (self.aluno, 403)]:
                with self.subTest(method=method, path=path, status=status):
                    response = self.client.open(path, method=method, headers=headers, json={})
                    self.assertEqual(response.status_code, status)
        self.get_db.assert_not_called()

    def test_secretaria_pode_aprovar_item(self):
        response = self.client.put('/api/itens/1/aprovar', headers=self.secretaria, json={})
        self.assertEqual(response.status_code, 200)
        self.connection.commit.assert_called_once()

    def test_categorias_listagem_publica_e_criacao_autorizada(self):
        self.assertEqual(self.client.get('/api/categorias').status_code, 200)
        self.assertEqual(self.client.post('/api/categorias', headers=self.secretaria,
                                         json={'nome': 'OUTROS'}).status_code, 200)

    def test_preflight_continua_publico(self):
        for path in ['/api/categorias', '/api/chat/enviar', '/api/itens/1/aprovar']:
            self.assertEqual(self.client.options(path).status_code, 200)
        self.get_db.assert_not_called()

    def test_chat_exige_autenticacao_e_rm_proprio(self):
        for method, path in [('GET', '/api/chat/mensagens/12345'),
                             ('POST', '/api/chat/enviar')]:
            self.assertEqual(self.client.open(path, method=method, json={}).status_code, 401)
        self.assertEqual(self.client.get('/api/chat/mensagens/99999',
                                        headers=self.aluno).status_code, 403)
        self.assertEqual(self.client.post('/api/chat/enviar', headers=self.aluno,
                         json={'rm': '99999', 'mensagem': 'Oi'}).status_code, 403)
        self.get_db.assert_not_called()

    def test_chat_nao_permite_rm_compartilhado(self):
        for rm in ['ALUNO', 'PENDENTE', 'PROFESSOR']:
            token = server.gerar_token_aluno('teste@cps.sp.gov.br', 'Teste', rm)
            response = self.client.get('/api/chat/mensagens/' + rm,
                                      headers={'Authorization': 'Bearer ' + token})
            self.assertEqual(response.status_code, 403)
        self.get_db.assert_not_called()

    def test_chat_ignora_nome_e_remetente_forjados(self):
        response = self.client.post('/api/chat/enviar', headers=self.aluno,
            json={'rm': '12345', 'nome': 'Secretaria', 'remetente': 'SECRETARIA', 'mensagem': 'Oi'})
        self.assertEqual(response.status_code, 200)
        params = self.cursor.execute.call_args.args[1]
        self.assertEqual(params[:4], ('12345', 'Nome real', 'ALUNO', 'Oi'))

    def test_secretaria_pode_enviar_resposta_com_remetente_da_sessao(self):
        response = self.client.post('/api/chat/enviar', headers=self.secretaria,
            json={'rm': '12345', 'remetente': 'ALUNO', 'mensagem': 'Resposta'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.cursor.execute.call_args.args[1][2], 'SECRETARIA')

    def test_leitura_chat_usa_sessao_para_marcar_lidas(self):
        self.cursor.fetchall.return_value = [{'mensagem': 'Oi'}]
        for headers, origem_falsa, esperado in [
            (self.aluno, 'SECRETARIA', 'SECRETARIA'),
            (self.secretaria, 'ALUNO', 'ALUNO')]:
            response = self.client.get('/api/chat/mensagens/12345?marcar_lida=true&origem=' + origem_falsa,
                                       headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.cursor.execute.call_args.args[1], ('12345', esperado))

    def test_validacao_da_rota_e_a_mesma_dos_testes(self):
        self.assertIs(server.validar_email_institucional, validar_email_institucional)
        for email in ['professor@cps.sp.gov.br', 'secretaria@etec.sp.gov.br']:
            self.assertTrue(server.validar_email_institucional(email)[0])
        for email in ['@aluno.cps.sp.gov.br', 'a@@aluno.cps.sp.gov.br', 123]:
            self.assertEqual(self.client.post('/api/auth/enviar-codigo',
                             json={'email': email}).status_code, 400)
        self.get_db.assert_not_called()

    def test_doacoes_contagem_e_conclusao_preservam_historico(self):
        # Executa o SQL emitido pelas rotas em uma tabela temporária, sem banco real.
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.row_factory = sqlite3.Row
        db.executescript('''CREATE TABLE itens (
            id INTEGER PRIMARY KEY, status TEXT, aprovado BOOLEAN, categoria TEXT,
            local_encontrado TEXT); CREATE TABLE entregues (id INTEGER);''')
        statuses = ['PARA DOAÇÃO', 'PARA DOACAO', 'DOAÇÃO', 'DOACAO',
                    'DOAÇÃO FEITA', 'DISPONÍVEL', 'ENTREGUE', 'SOLICITADO']
        for i, status in enumerate(statuses, 1):
            db.execute('INSERT INTO itens VALUES (?, ?, TRUE, ?, ?)', (i, status, 'OUTROS', 'Pátio'))
        db.execute("INSERT INTO itens VALUES (9, 'PARA DOAÇÃO', FALSE, 'OUTROS', 'Pátio')")
        sql_cursor = db.cursor()
        self.cursor.execute.side_effect = lambda query, *args: sql_cursor.execute(query, *args)
        self.cursor.fetchone.side_effect = lambda: dict(sql_cursor.fetchone())
        self.cursor.fetchall.side_effect = lambda: [dict(row) for row in sql_cursor.fetchall()]
        with patch.object(server, 'verificar_e_atualizar_itens_doacao'):
            stats = self.client.get('/api/estatisticas', headers=self.secretaria)
            self.assertEqual(stats.status_code, 200)
            self.assertEqual(stats.json['total_doacoes'], 4)
            response = self.client.delete('/api/itens/doacoes/concluir', headers=self.secretaria)
            self.assertEqual(response.status_code, 200)
            stats = self.client.get('/api/estatisticas', headers=self.secretaria)
            self.assertEqual(stats.json['total_doacoes'], 0)
        rows = db.execute('SELECT id, status FROM itens ORDER BY id').fetchall()
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row['status'] == 'DOAÇÃO FEITA' for row in rows[:5]))
        self.assertEqual(rows[5]['status'], 'DISPONÍVEL')
        self.assertEqual(rows[8]['status'], 'PARA DOAÇÃO')
        self.assertEqual(self.client.delete('/api/itens/doacoes/concluir',
                                           headers=self.secretaria).status_code, 200)


class ModularRouteTests(RouteTests):
    """Repete os contratos na implementação modular para evitar divergências."""
    def setUp(self):
        super().setUp()
        from flask import Flask
        from blueprints import auth, chat, itens, mural, relatorios
        app = Flask(__name__)
        app.config['TESTING'] = True
        for module, blueprint in [(auth, auth.auth_bp), (chat, chat.chat_bp),
                                  (itens, itens.itens_bp), (mural, mural.mural_bp),
                                  (relatorios, relatorios.relatorios_bp)]:
            app.register_blueprint(blueprint)
            patcher = patch.object(module, 'get_db_connection', return_value=self.connection)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(relatorios, 'verificar_e_atualizar_itens_doacao')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app.test_client()
