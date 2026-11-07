"""Regressões das rotas reais sem acesso a banco ou integrações externas.

Execute com DATABASE_URL vazio e JWT_SECRET de teste definido no ambiente.
"""
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

import server
from utils.helpers import validar_email_institucional


class ErrorPageTests(unittest.TestCase):
    def setUp(self):
        server.app.config['TESTING'] = True
        server.limiter.enabled = False
        self.client = server.app.test_client()
        patcher = patch.object(server, 'get_db_connection')
        self.get_db = patcher.start()
        self.addCleanup(patcher.stop)

    def test_404_html_aninhado_e_recursos_do_jogo_sem_banco(self):
        response = self.client.get('/uma/pagina/que-nao-existe', headers={'Accept': 'text/html'})
        self.assertEqual(response.status_code, 404)
        self.assertIn('Operação Achados', response.get_data(as_text=True))
        for asset, content_type in [('/jogo-404.css', 'text/css'), ('/jogo-404.js', 'javascript')]:
            resource = self.client.get(asset)
            self.assertEqual(resource.status_code, 200)
            self.assertIn(content_type, resource.content_type)
            resource.close()
        self.get_db.assert_not_called()
        response.close()

    def test_404_api_continua_json_mesmo_com_accept_html(self):
        for path in ['/api/rota-inexistente', '/nao-existe.js']:
            headers = {'Accept': 'text/html'} if path.startswith('/api/') else {}
            response = self.client.get(path, headers=headers)
            self.assertEqual(response.status_code, 404)
            self.assertIsNotNone(response.get_json())
            self.assertNotIn(b'jogo-404', response.data)
        self.get_db.assert_not_called()


class RouteTests(unittest.TestCase):
    def setUp(self):
        server.app.config['TESTING'] = True
        server.limiter.enabled = False
        self.client = server.app.test_client()
        permission_patch = patch('services.professores_service.buscar_acesso', return_value=None)
        permission_patch.start()
        self.addCleanup(permission_patch.stop)
        self.aluno = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
            'aluno@aluno.cps.sp.gov.br', 'Nome real', '12345')}
        self.secretaria = {'Authorization': 'Bearer ' + server.gerar_token_secretaria(
            'secretaria@etec.sp.gov.br')}
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.__enter__.return_value = self.cursor
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
        for path in ['/api/categorias', '/api/chat/enviar', '/api/itens/1/aprovar',
                     '/api/solicitar', '/api/mural', '/api/itens/cadastrar-aluno']:
            self.assertEqual(self.client.options(path).status_code, 200)
        self.get_db.assert_not_called()

    def test_escritas_de_aluno_rejeitam_anonimo_e_token_invalido_antes_de_fotos_ou_banco(self):
        with patch('server.processar_fotos') as fotos_unificado, \
             patch('blueprints.itens.processar_fotos') as fotos_modular:
            for path in ['/api/solicitar', '/api/mural', '/api/itens/cadastrar-aluno']:
                for headers in [{}, {'Authorization': 'Bearer forjado'}]:
                    response = self.client.post(path, headers=headers, json={
                        'id': 7, 'nome': 'Outra pessoa', 'rm': '99999',
                        'email': 'outra@aluno.cps.sp.gov.br', 'foto': 'foto-forjada'})
                    self.assertEqual(response.status_code, 401, path)
            fotos_unificado.assert_not_called()
            fotos_modular.assert_not_called()
        self.get_db.assert_not_called()

    def test_solicitacao_usa_identidade_assinada_e_funciona_so_com_id(self):
        self.cursor.rowcount = 1
        for body in [{'id': 7}, {'id': 7, 'nome': 'Terceiro', 'rm': '99999',
                                'email': 'terceiro@aluno.cps.sp.gov.br', 'role': 'secretaria'}]:
            result = self.client.post('/api/solicitar', headers=self.aluno, json=body)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(self.cursor.execute.call_args.args[1],
                             ('Nome real', '12345', 'aluno@aluno.cps.sp.gov.br', 7))

    def test_mural_ignora_identidade_informada_no_corpo(self):
        result = self.client.post('/api/mural', headers=self.aluno, json={
            'nome': 'Terceiro', 'rm': '99999', 'email': 'terceiro@aluno.cps.sp.gov.br',
            'categoria': 'OUTROS', 'descricao': 'Perdi meu estojo'})
        self.assertEqual(result.status_code, 200)
        inserts = [call for call in self.cursor.execute.call_args_list
                   if 'INSERT INTO mural_perdidos' in call.args[0]]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(inserts[0].args[1][:5],
                         ('Nome real', '12345', 'aluno@aluno.cps.sp.gov.br', 'OUTROS', 'Perdi meu estojo'))

    def test_cadastro_objeto_usa_rm_assinado_e_mantem_titulo_e_moderacao(self):
        with patch('server.processar_fotos', return_value=[]), \
             patch('blueprints.itens.processar_fotos', return_value=[]):
            result = self.client.post('/api/itens/cadastrar-aluno', headers=self.aluno,
                json={'nome': 'Estojo preto', 'descricao': 'Encontrado no pátio', 'rm': '99999'})
        self.assertEqual(result.status_code, 200)
        query, params = self.cursor.execute.call_args.args
        self.assertIn('FALSE, TRUE', query)
        self.assertEqual(params[0], 'Estojo preto')
        self.assertEqual(params[-2:], ('12345', 'aluno@aluno.cps.sp.gov.br'))

    def test_professor_nao_pode_se_passar_por_aluno_mesmo_com_acesso_ao_painel(self):
        for acesso in [None, {'status': 'APROVADO'}]:
            with patch('services.professores_service.buscar_acesso', return_value=acesso):
                professor = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
                    'docente@etec.sp.gov.br', 'Docente', '12345')}
                for path in ['/api/solicitar', '/api/mural']:
                    result = self.client.post(path, headers=professor, json={
                        'id': 7, 'nome': 'Aluno', 'rm': '99999', 'email': 'aluno@aluno.cps.sp.gov.br'})
                    self.assertEqual(result.status_code, 403)
        self.get_db.assert_not_called()

    def test_professor_ainda_pode_cadastrar_objetos_sem_usar_rm_de_aluno(self):
        for acesso in [None, {'status': 'APROVADO'}]:
            with patch('services.professores_service.buscar_acesso', return_value=acesso), \
                 patch('server.processar_fotos', return_value=[]), \
                 patch('blueprints.itens.processar_fotos', return_value=[]):
                professor = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
                    'docente@etec.sp.gov.br', 'Docente', '12345')}
                result = self.client.post('/api/itens/cadastrar-aluno', headers=professor,
                    json={'nome': 'Controle', 'descricao': 'Encontrado', 'rm': '99999'})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(self.cursor.execute.call_args.args[1][-2:], ('PROFESSOR', 'docente@etec.sp.gov.br'))

    def test_perfil_admin_e_rm_generico_nao_podem_solicitar_ou_publicar_com_identidade_falsa(self):
        tokens = [self.secretaria]
        for rm in ['ALUNO', 'PENDENTE', 'PROFESSOR', '']:
            tokens.append({'Authorization': 'Bearer ' + server.gerar_token_aluno(
                'aluno@aluno.cps.sp.gov.br', 'Aluno', rm)})
        for headers in tokens:
            for path in ['/api/solicitar', '/api/mural']:
                self.assertEqual(self.client.post(path, headers=headers, json={
                    'id': 7, 'rm': '99999', 'email': 'terceiro@aluno.cps.sp.gov.br'}).status_code, 403)
        self.get_db.assert_not_called()

    def test_palavra_professor_no_email_de_aluno_nao_bloqueia_solicitacao(self):
        self.cursor.rowcount = 1
        headers = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
            'professor.nome@aluno.cps.sp.gov.br', 'Aluno', '12345')}
        result = self.client.post('/api/solicitar', headers=headers, json={'id': 7})
        self.assertEqual(result.status_code, 200)

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
        self.cursor.fetchone.return_value={'nome':'Aluno','rm':'12345','email':'aluno@aluno.cps.sp.gov.br'}
        response = self.client.post('/api/chat/enviar', headers=self.secretaria,
            json={'rm': '12345', 'email':'aluno@aluno.cps.sp.gov.br', 'remetente': 'ALUNO', 'mensagem': 'Resposta'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.cursor.execute.call_args.args[1][2], 'SECRETARIA')

    def test_leitura_chat_usa_sessao_para_marcar_lidas(self):
        self.cursor.fetchall.return_value = [{'id':1,'mensagem': 'Oi'}]
        self.cursor.fetchone.return_value={'nome':'Aluno','rm':'12345','email':'aluno@aluno.cps.sp.gov.br'}
        for headers, origem_falsa, esperado in [
            (self.aluno, 'SECRETARIA', 'SECRETARIA'),
            (self.secretaria, 'ALUNO', 'ALUNO')]:
            response = self.client.get('/api/chat/mensagens/12345?email=aluno@aluno.cps.sp.gov.br&marcar_lida=true&origem=' + origem_falsa,
                                       headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.cursor.execute.call_args.args[1], ('aluno@aluno.cps.sp.gov.br', esperado, 1))

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
            local_encontrado TEXT); CREATE TABLE entregues (id INTEGER,cancelada_em TEXT);''')
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

    def test_login_compartilhado_professor_rejeitado(self):
        self.cursor.fetchone.return_value = None
        result = self.client.post('/api/auth/login-aluno', json={'email': 'professor', 'senha': 'professor'})
        self.assertEqual(result.status_code, 401)
        self.assertNotIn('token', result.json)

    def test_professor_cadastrado_usa_senha_individual(self):
        from werkzeug.security import generate_password_hash
        self.cursor.fetchone.return_value = {
            'email': 'docente@cps.sp.gov.br', 'nome': 'Docente', 'rm': 'PROFESSOR',
            'senha_hash': generate_password_hash('SenhaComMaiusculas123!')}
        result = self.client.post('/api/auth/login-aluno', json={
            'email': 'docente@cps.sp.gov.br', 'senha': 'SenhaComMaiusculas123!'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['aluno']['email'], 'docente@cps.sp.gov.br')
        denied = self.client.post('/api/auth/login-aluno', json={
            'email': 'docente@cps.sp.gov.br', 'senha': 'professor'})
        self.assertEqual(denied.status_code, 401)
        self.assertNotIn('token', denied.json)

    def test_tokens_da_antiga_conta_compartilhada_sao_revogados(self):
        import jwt
        from datetime import datetime, timedelta, timezone
        token = jwt.encode({'email': 'professor@cps.sp.gov.br', 'nome': 'Professor(a)',
                            'rm': 'PROFESSOR', 'role': 'aluno',
                            'exp': datetime.now(timezone.utc) + timedelta(days=1)},
                           server.JWT_SECRET, algorithm='HS256')
        result = self.client.get('/api/chat/mensagens/12345', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(result.status_code, 401)
        self.assertTrue(result.json['expired'])
        self.get_db.assert_not_called()


    def test_catalogo_publico_oculta_dados_pessoais_mesmo_com_token_aluno(self):
        row = {'id': 1, 'nome': 'Estojo', 'status': 'SOLICITADO',
               'solicitado_por': 'Nome privado', 'rm_aluno': '99999',
               'email_solicitante': 'privado@aluno.cps.sp.gov.br', 'campo_novo_privado': 'segredo'}
        self.cursor.fetchall.side_effect = lambda: [dict(row)]
        with patch.object(server, 'verificar_e_atualizar_itens_doacao'):
            for headers in [{}, self.aluno]:
                result = self.client.get('/api/itens', headers=headers)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json[0]['nome'], 'Estojo')
                for field in ['solicitado_por','rm_aluno','email_solicitante','campo_novo_privado']:
                    self.assertNotIn(field, result.json[0])
                self.assertIn('no-store', result.headers['Cache-Control'])

    def test_secretaria_preserva_dados_administrativos_do_catalogo(self):
        self.cursor.fetchall.return_value = [{'id': 1, 'solicitado_por': 'Aluno', 'rm_aluno': '12345'}]
        with patch.object(server, 'verificar_e_atualizar_itens_doacao'):
            result = self.client.get('/api/itens', headers=self.secretaria)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json[0]['rm_aluno'], '12345')
        self.assertIn('no-store', result.headers['Cache-Control'])

    def test_mural_publico_anonimiza_autor_e_admin_preserva_dados(self):
        self.cursor.fetchall.return_value = [{'id':1,'descricao':'Perdi um estojo',
            'nome_aluno':'Nome privado','rm_aluno':'99999','email_aluno':'privado@cps.sp.gov.br'}]
        for headers in [{}, self.aluno]:
            result = self.client.get('/api/mural', headers=headers)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json[0]['nome_aluno'], 'Aluno')
            self.assertNotIn('rm_aluno', result.json[0])
            self.assertNotIn('email_aluno', result.json[0])
        result = self.client.get('/api/mural', headers=self.secretaria)
        self.assertEqual(result.json[0]['nome_aluno'], 'Nome privado')
        self.assertIn('no-store', result.headers['Cache-Control'])

    def test_consultas_publicas_rejeitam_token_forjado(self):
        for path in ['/api/itens','/api/mural']:
            result = self.client.get(path, headers={'Authorization':'Bearer forjado'})
            self.assertEqual(result.status_code, 401)
        self.get_db.assert_not_called()

    def test_meus_itens_filtra_email_assinado_sem_usar_nome_ou_rm_enviado(self):
        self.assertEqual(self.client.get('/api/itens/meus').status_code, 401)
        result = self.client.get('/api/itens/meus?rm=99999&email=terceiro@cps.sp.gov.br', headers=self.aluno)
        self.assertEqual(result.status_code, 200)
        query, params = self.cursor.execute.call_args.args
        self.assertIn('email_solicitante = %s', query)
        self.assertEqual(params, ('aluno@aluno.cps.sp.gov.br',))
        self.assertIn('no-store', result.headers['Cache-Control'])

    def test_relatos_pessoais_exigem_sessao_e_filtram_email(self):
        self.assertEqual(self.client.get('/api/mural/aluno/12345').status_code, 401)
        self.assertEqual(self.client.get('/api/mural/aluno/99999', headers=self.aluno).status_code, 403)
        result = self.client.get('/api/mural/aluno/12345', headers=self.aluno)
        self.assertEqual(result.status_code, 200)
        query, params = self.cursor.execute.call_args.args
        self.assertIn('email_aluno = %s', query)
        self.assertEqual(params, ('aluno@aluno.cps.sp.gov.br',))



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
