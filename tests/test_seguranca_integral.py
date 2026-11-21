"""Abusos reais de autenticação/HTTP em banco isolado, sem e-mails externos."""
import threading,uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import pytest,jwt
from werkzeug.security import generate_password_hash
import server,database
from config import JWT_SECRET
from services import autenticacao_service as acesso,cloudinary_service
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth
from utils.perfis import VERSAO_TERMOS

A='a@aluno.cps.sp.gov.br';B='b@aluno.cps.sp.gov.br';SENHA='Minha senha segura 123!'


@pytest.fixture
def ambiente(db,monkeypatch):
    mensagens=[]
    monkeypatch.setattr('services.email_service.enviar_confirmacao',lambda email,codigo,finalidade:mensagens.append((email,codigo,finalidade)) or True)
    with db() as co:
        with co.cursor() as c:c.execute('UPDATE alunos SET senha_hash=%s',(generate_password_hash(SENHA),))
    return server.app.test_client(),db,mensagens


def emitir(client,mensagens,email=A,finalidade='recuperacao'):
    res=client.post('/api/auth/enviar-codigo',json=dict(email=email,finalidade=finalidade));assert res.status_code==200,res.json
    return mensagens[-1][1]


def claims(token):return jwt.decode(token,JWT_SECRET,algorithms=['HS256'],audience='etec-portal',issuer='etec-achados')


def test_codigo_so_guarda_hmac_nao_pode_trocar_finalidade_e_tem_cinco_erros(ambiente):
    c,db,m=ambiente;codigo=emitir(c,m)
    assert scalar(db,'SELECT codigo FROM codigos_auth')!=codigo
    assert scalar(db,'SELECT length(codigo) FROM codigos_auth')==64
    payload=dict(email=A,codigo=codigo,nome='Aluno Teste',rm='12345',senha=SENHA,aceite_termos=True,versao_termos=VERSAO_TERMOS)
    assert c.post('/api/auth/cadastrar',json=payload).status_code==400
    errado='000000' if codigo!='000000' else '111111'
    for _ in range(5):assert c.post('/api/auth/redefinir',json=dict(email=A,codigo=errado,senha=SENHA)).status_code==400
    assert scalar(db,'SELECT tentativas FROM codigos_auth')==5
    assert c.post('/api/auth/redefinir',json=dict(email=A,codigo=codigo,senha=SENHA)).status_code==400


def test_reset_invalida_todos_tokens_antigos_e_codigo_so_funciona_uma_vez(ambiente):
    c,db,m=ambiente;antigo=auth();outro=auth();b=auth(B);codigo=emitir(c,m)
    assert c.get('/api/perfil',headers=antigo).status_code==200
    body=dict(email=A,codigo=codigo,senha='Outra senha segura 456!')
    assert c.post('/api/auth/redefinir',json=body).status_code==200
    for h in [antigo,outro]:assert c.get('/api/perfil',headers=h).status_code==401
    assert c.get('/api/perfil',headers=b).status_code==200
    assert c.post('/api/auth/redefinir',json=body).status_code==400
    assert c.post('/api/auth/login-aluno',json=dict(email=A,senha=SENHA)).status_code==401
    nova=c.post('/api/auth/login-aluno',json=dict(email=A,senha=body['senha']));assert nova.status_code==200,nova.json
    assert c.get('/api/perfil',headers={'Authorization':'Bearer '+nova.json['token']}).status_code==200


def test_logout_revoga_apenas_o_token_em_uso(ambiente):
    c,db,_=ambiente;um=auth();dois=auth()
    assert c.post('/api/auth/sair',headers=um).status_code==200
    assert c.get('/api/perfil',headers=um).status_code==401
    assert c.get('/api/perfil',headers=dois).status_code==200
    assert scalar(db,'SELECT count(*) FROM auth_tokens_revogados')==1


def test_limpeza_de_logout_respeita_tolerancia_de_expiracao(ambiente):
    import time
    c,db,_=ambiente;payload=claims(auth()['Authorization'][7:]);payload['exp']=time.time()-10
    antigo={'Authorization':'Bearer '+jwt.encode(payload,JWT_SECRET,algorithm='HS256')}
    assert c.post('/api/auth/sair',headers=antigo).status_code==200
    assert c.post('/api/auth/sair',headers=auth()).status_code==200
    assert c.get('/api/perfil',headers=antigo).status_code==401


def test_admin_prioriza_hash_e_limita_erros_por_conta(ambiente,monkeypatch):
    c,db,_=ambiente;email='secretaria@etec.sp.gov.br'
    monkeypatch.setattr(server,'EMAIL_SECRETARIA',email)
    monkeypatch.setattr(server,'ADMIN_SENHA_HASH',generate_password_hash(SENHA))
    monkeypatch.setattr(server,'ADMIN_SENHA','alternativa-plana-ignorada')
    assert c.post('/api/login',json=dict(email=email,senha='alternativa-plana-ignorada')).status_code==401
    assert c.post('/api/login',json=dict(email=email,senha=SENHA)).status_code==200
    for _ in range(8):assert c.post('/api/login',json=dict(email=email,senha='errada')).status_code==401
    assert c.post('/api/login',json=dict(email=email,senha=SENHA)).status_code==429


def test_atualizar_rm_preserva_sessao_e_nao_contorna_reset(ambiente):
    c,db,m=ambiente;headers=auth();antes=claims(headers['Authorization'][7:])
    res=c.post('/api/auth/atualizar-rm',headers=headers,json={'rm':'99999'});assert res.status_code==200,res.json
    novo=res.json['token'];depois=claims(novo)
    for campo in ['iat','jti','exp']:assert antes[campo]==depois[campo]
    codigo=emitir(c,m)
    assert c.post('/api/auth/redefinir',json=dict(email=A,codigo=codigo,senha=SENHA)).status_code==200
    assert c.get('/api/perfil',headers={'Authorization':'Bearer '+novo}).status_code==401


def test_login_e_reset_concorrentes_nao_criam_sessao_posterior_ao_reset(ambiente,monkeypatch):
    from utils import security
    c,db,m=ambiente;codigo=emitir(c,m)
    entrou=threading.Event();reset_terminou=threading.Event();original=security.gerar_token_aluno
    def assinar(*args,**kwargs):
        entrou.set();reset_terminou.wait(.3)
        return original(*args,**kwargs)
    monkeypatch.setattr(security,'gerar_token_aluno',assinar)
    def login():return server.app.test_client().post('/api/auth/login-aluno',json=dict(email=A,senha=SENHA))
    def redefinir():
        r=server.app.test_client().post('/api/auth/redefinir',json=dict(email=A,codigo=codigo,senha='Outra senha segura 456!'));reset_terminou.set();return r
    with ThreadPoolExecutor(max_workers=2) as pool:
        l=pool.submit(login);assert entrou.wait(5);r=pool.submit(redefinir)
        login_res,reset_res=l.result(timeout=10),r.result(timeout=10)
    assert login_res.status_code==reset_res.status_code==200
    assert c.get('/api/perfil',headers={'Authorization':'Bearer '+login_res.json['token']}).status_code==401


def test_duas_confirmacoes_concorrentes_nao_reutilizam_codigo(ambiente):
    c,db,m=ambiente;codigo=emitir(c,m)
    def redefinir(_):return server.app.test_client().post('/api/auth/redefinir',json=dict(email=A,codigo=codigo,senha=SENHA)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(redefinir,range(2)))==[200,400]


def test_login_bloqueia_conta_mesmo_com_ips_diferentes(ambiente):
    c,db,_=ambiente
    for i in range(8):assert c.post('/api/auth/login-aluno',json=dict(email=A,senha='errada'),environ_base={'REMOTE_ADDR':'192.0.2.'+str(i+1)}).status_code==401
    assert c.post('/api/auth/login-aluno',json=dict(email=A,senha=SENHA)).status_code==429
    assert c.post('/api/auth/login-aluno',json=dict(email=B,senha=SENHA)).status_code==200


def test_reenvio_tem_intervalo_e_limite_persistente(ambiente):
    c,db,m=ambiente;primeiro=emitir(c,m)
    assert c.post('/api/auth/enviar-codigo',json=dict(email=A,finalidade='recuperacao')).status_code==429
    assert len(m)==1 and scalar(db,'SELECT codigo FROM codigos_auth')==acesso.resumo_codigo(A,'recuperacao',primeiro)
    with db() as co:
        with co.cursor() as cur:cur.execute("UPDATE codigos_auth SET enviado_em=CURRENT_TIMESTAMP-INTERVAL '61 seconds'")
    emitir(c,m)
    assert c.post('/api/auth/enviar-codigo',json=dict(email=A,finalidade='recuperacao')).status_code==429
    assert len(m)==2


def test_provedor_recusou_nao_anuncia_email_enviado_nem_deixa_codigo(ambiente,monkeypatch):
    c,db,_=ambiente;monkeypatch.setattr('services.email_service.enviar_confirmacao',lambda *a:False)
    assert c.post('/api/auth/enviar-codigo',json=dict(email=A,finalidade='recuperacao')).status_code==503
    assert scalar(db,'SELECT count(*) FROM codigos_auth')==0


def test_conta_inexistente_e_existente_recebem_mesma_resposta(ambiente):
    c,db,m=ambiente
    r1=c.post('/api/auth/enviar-codigo',json=dict(email=A,finalidade='recuperacao'))
    r2=c.post('/api/auth/enviar-codigo',json=dict(email='ninguem@aluno.cps.sp.gov.br',finalidade='recuperacao'))
    assert r1.status_code==r2.status_code==200 and r1.json==r2.json and len(m)==1


@pytest.mark.parametrize('senha',['','curta','a'*129,[],None,12345,' '*12,'\t'*12,'\n\t '*6,'\u3000'*12])
def test_senha_fraca_ou_tipo_invalido_rejeitado_antes_do_codigo(senha):
    with patch.object(server,'get_db_connection') as banco:
        dados=dict(email=A,codigo='123456',senha=senha,nome='Aluno Teste',rm='12345',aceite_termos=True,versao_termos=VERSAO_TERMOS)
        for rota in ['/api/auth/redefinir','/api/auth/cadastrar']:
            assert server.app.test_client().post(rota,json=dados).status_code==400
        banco.assert_not_called()


def test_senha_vazia_na_recuperacao_nao_consume_codigo_nem_altera_a_conta(ambiente):
    c,db,m=ambiente;codigo=emitir(c,m)
    anterior=scalar(db,'SELECT senha_hash FROM alunos WHERE email=%s',(A,))
    dados=dict(email=A,codigo=codigo,senha=' '*12)
    resposta=c.post('/api/auth/redefinir',json=dados)
    assert resposta.status_code==400 and 'apenas espaços' in resposta.json['message']
    assert scalar(db,'SELECT senha_hash FROM alunos WHERE email=%s',(A,))==anterior
    assert scalar(db,'SELECT count(*) FROM auth_revogacoes')==0
    assert scalar(db,'SELECT tentativas FROM codigos_auth WHERE email=%s',(A,))==0
    assert c.post('/api/auth/redefinir',json={**dados,'senha':SENHA}).status_code==200


def test_tokens_anteriores_ou_claims_alterados_sao_rejeitados(monkeypatch):
    c=server.app.test_client();original=claims(auth()['Authorization'][7:])
    def proibido():raise AssertionError('Claims inválidos devem ser recusados antes do banco')
    monkeypatch.setattr(database,'get_db_connection',proibido)
    for mudanca in [{'auth_version':2},{'aud':'outro-site'},{'iss':'outro-emissor'},{'iat':True},{'jti':[]},{'email':[]}]:
        h={'Authorization':'Bearer '+jwt.encode({**original,**mudanca},JWT_SECRET,algorithm='HS256')}
        assert c.get('/api/perfil',headers=h).status_code==401,mudanca
    assert c.get('/api/perfil',headers={'Authorization':'Basic '+auth()['Authorization'][7:]}).status_code==401


def test_falha_do_banco_nao_valida_sessao_por_omissao(monkeypatch):
    c=server.app.test_client()
    def falhar():raise RuntimeError('detalhes privados de conexão')
    monkeypatch.setattr(database,'get_db_connection',falhar)
    r=c.get('/api/perfil',headers=auth());assert r.status_code==503 and b'privados' not in r.data


@pytest.mark.parametrize('body',[[],None,{'email':[]},{'email':A,'senha':{}},{'email':A,'senha':'a'*10000}])
def test_auth_json_malformado_nao_produz_erro_interno(body):
    c=server.app.test_client()
    with patch.object(server,'get_db_connection') as banco:
        for path in ['/api/auth/cadastrar','/api/auth/redefinir','/api/auth/login-aluno','/api/login']:
            r=c.post(path,json=body);assert r.status_code in (400,401,415),r.json
        banco.assert_not_called()


def test_cors_rejeita_site_estranho_e_nao_permite_origem_null():
    c=server.app.test_client()
    for origin in ['https://invasor.invalid','null','https://localhost.invasor.invalid']:
        r=c.options('/api/auth/login-aluno',headers={'Origin':origin,'Access-Control-Request-Method':'POST'})
        assert r.status_code==403 and 'Access-Control-Allow-Origin' not in r.headers
    r=c.options('/api/auth/login-aluno',headers={'Origin':'http://localhost'})
    assert r.status_code==200 and r.headers['Access-Control-Allow-Origin']=='http://localhost'


def test_cabecalhos_csp_hsts_e_cache_privado():
    c=server.app.test_client();r=c.get('/',base_url='https://localhost');assert r.status_code==200
    assert r.headers['X-Frame-Options']=='DENY'
    assert "object-src 'none'" in r.headers['Content-Security-Policy']
    assert 'unsafe-eval' not in r.headers['Content-Security-Policy']
    assert 'max-age=31536000'==r.headers['Strict-Transport-Security']
    assert 'Strict-Transport-Security' not in c.get('/').headers
    assert 'no-store' in c.get('/api/auth/verificar').headers['Cache-Control']
    for path in ['/.env','/server.py','/config.py','/requirements.txt','/tests/test_seguranca_integral.py']:
        assert c.get(path).status_code==404


def test_requisicao_de_login_grande_rejeitada_antes_do_banco():
    with patch.object(server,'get_db_connection') as banco:
        assert server.app.test_client().post('/api/auth/login-aluno',json=dict(email=A,senha='x'*20000)).status_code==413
        banco.assert_not_called()


def test_link_de_foto_pronta_de_outra_conta_nao_e_reaproveitado(ambiente,monkeypatch):
    c,db,_=ambiente;url='https://res.cloudinary.com/teste/image/upload/etec_achados/foto.jpg'
    monkeypatch.setattr(cloudinary_service,'CLOUDINARY_CLOUD_NAME','teste')
    with db() as co:
        with co.cursor() as cur:cur.execute('INSERT INTO uploads_fotos(id,email,tamanho,sha256,recebidos,url) VALUES(%s,%s,1,%s,1,%s)',(str(uuid.uuid4()),A,'a'*64,url))
    with server.app.test_request_context('/'):
        from flask import request
        request.user={'email':B}
        with pytest.raises(cloudinary_service.FotoInvalida):cloudinary_service.processar_fotos([url])
        request.user={'email':A};assert cloudinary_service.processar_fotos([url])==[url]


@pytest.mark.parametrize('destino',['http://site.invalid/api/login','https://outro.invalid/api/login','https://etec-achados.up.railway.app.invasor.invalid/api/login'])
def test_desktop_nunca_envia_credenciais_ao_destino_incorreto(destino):
    from desktop_secretaria import requisicao_desktop
    with patch('desktop_secretaria.requests.request') as http:
        with pytest.raises(ValueError):requisicao_desktop('POST',destino,json={'senha':SENHA})
        http.assert_not_called()


@pytest.mark.parametrize('opcoes',[{'headers':{'authorization':'Bearer segredo'}},{'headers':{'x-access-token':'segredo'}},{'data':{'senha':SENHA}}])
def test_desktop_tambem_protege_cabecalhos_minusculos_e_formularios(opcoes):
    from desktop_secretaria import requisicao_desktop
    with patch('desktop_secretaria.requests.request') as http:
        with pytest.raises(ValueError):requisicao_desktop('POST','http://invasor.invalid/api/login',**opcoes)
        http.assert_not_called()


def test_desktop_nao_segue_redirect_nem_desliga_tls():
    import desktop_secretaria as desktop
    with patch('desktop_secretaria.requests.request') as http:
        http.return_value.status_code=307;http.return_value.ok=True
        desktop.requisicao_desktop('POST',desktop.API_URL+'/api/login',json={'senha':SENHA})
        assert http.call_args.kwargs['allow_redirects'] is False
        with pytest.raises(ValueError):desktop.requisicao_desktop('GET',desktop.API_URL+'/api/itens',verify=False)


@pytest.mark.parametrize('body',[{'texto_a':'x'*2001},{'texto_b':['texto']},[]])
def test_comparacao_publica_recusa_textos_grandes_e_tipos_invalidos(body):
    assert server.app.test_client().post('/api/ia/comparar-semantica',json=body).status_code==400
