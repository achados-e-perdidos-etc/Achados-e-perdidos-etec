"""Ambiente de demonstração: isolamento, SSL configurável e preparo idempotente."""
import importlib.util,json,os,subprocess,sys
from pathlib import Path
import pytest
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db
from werkzeug.security import check_password_hash


@pytest.fixture
def ambiente(tmp_path,monkeypatch):
    for key in ['DATABASE_URL','DATABASE_SSLMODE','JWT_SECRET','ADMIN_EMAIL','ADMIN_SENHA','ADMIN_SENHA_HASH','PORT']:
        monkeypatch.setenv(key,os.environ.get(key,''))
    spec=importlib.util.spec_from_file_location('ambiente_codespaces',Path(__file__).resolve().parents[1]/'.devcontainer/ambiente.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    monkeypatch.setattr(mod,'ARQUIVO',tmp_path/'.env.codespaces.json')
    return mod


def test_preparo_exige_ambiente_explicito_e_isola_banco(ambiente,monkeypatch):
    monkeypatch.delenv('ETEC_CODESPACES_TESTE',raising=False)
    with pytest.raises(RuntimeError):ambiente.configurar()
    assert not ambiente.ARQUIVO.exists()
    monkeypatch.setenv('ETEC_CODESPACES_TESTE','1');monkeypatch.setenv('DATABASE_URL','postgresql://banco-real/nao-usar')
    a=ambiente.configurar();b=ambiente.configurar()
    assert a==b and len(a['jwt'])>=32 and len(a['senha'])>=16
    assert os.environ['DATABASE_URL']==ambiente.BANCO and os.environ['DATABASE_SSLMODE']=='disable'
    assert not os.environ['ADMIN_SENHA'] and check_password_hash(os.environ['ADMIN_SENHA_HASH'],a['senha'])
    assert ambiente.ARQUIVO.stat().st_mode&0o077==0


def test_preparo_real_de_contas_e_objetos_idempotente(db,ambiente,monkeypatch):
    monkeypatch.setenv('ETEC_CODESPACES_TESTE','1');monkeypatch.setattr(ambiente,'esperar_banco',lambda:None)
    ambiente.preparar();dados=json.loads(ambiente.ARQUIVO.read_text())
    with db() as conn:
        with conn.cursor() as c:
            c.execute('SELECT senha_hash FROM alunos WHERE email=%s',(ambiente.CONTAS[0][0],));primeiro=c.fetchone()[0]
    assert check_password_hash(primeiro,dados['senha'])
    ambiente.preparar()
    assert scalar(db,"SELECT count(*) FROM alunos WHERE email IN ('aluno@aluno.cps.sp.gov.br','colega@aluno.cps.sp.gov.br','professor@etec.sp.gov.br')")==3
    assert scalar(db,"SELECT count(*) FROM itens WHERE descricao='Objeto fictício para testar o portal.'")==2
    assert scalar(db,'SELECT senha_hash FROM alunos WHERE email=%s',(ambiente.CONTAS[0][0],))==primeiro
    import server
    client=server.app.test_client();res=client.post('/api/auth/login-aluno',json={'email':ambiente.CONTAS[0][0],'senha':dados['senha']})
    assert res.status_code==200 and res.json['success']
    assert len(client.get('/api/catalogo').json['itens'])==2


def test_ssl_exige_protecao_por_padrao_e_aceita_banco_local_explicito():
    raiz=Path(__file__).resolve().parents[1]
    env=dict(os.environ,JWT_SECRET='segredo-local-de-teste-com-32-bytes',DATABASE_URL='')
    for valor,esperado in [(None,'require'),('disable','disable'),('verify-full','verify-full')]:
        atual=dict(env);atual.pop('DATABASE_SSLMODE',None)
        if valor is not None:atual['DATABASE_SSLMODE']=valor
        r=subprocess.run([sys.executable,'-c','import config;print(config.DATABASE_SSLMODE)'],cwd=raiz,env=atual,capture_output=True,text=True)
        assert r.returncode==0 and r.stdout.strip()==esperado
    r=subprocess.run([sys.executable,'-c','import config'],cwd=raiz,env=dict(env,DATABASE_SSLMODE='incorreto'),capture_output=True,text=True)
    assert r.returncode!=0 and 'DATABASE_SSLMODE inválido' in r.stderr
