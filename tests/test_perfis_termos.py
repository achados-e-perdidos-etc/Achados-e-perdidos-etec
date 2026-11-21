"""Foto privada, enquadramento real e aceite atômico em PostgreSQL temporário."""
import base64,io
from datetime import datetime,timedelta
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
from flask import Flask
from werkzeug.security import check_password_hash
import server
from blueprints import auth as auth_module
from services.foto_perfil import preparar_foto
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,item
from utils.perfis import VERSAO_TERMOS,SECOES_TERMOS

ROSTO=Path(__file__).parent/'fixtures/rosto_teste.jpg'
EMAIL='a@aluno.cps.sp.gov.br'
ADMIN=auth('secretaria@etec.sp.gov.br',True)


def uri(raw):return 'data:image/jpeg;base64,'+base64.b64encode(raw).decode()


def modificada(tipo):
    with Image.open(ROSTO) as original:foto=original.copy()
    if tipo=='dois':
        dupla=Image.new('RGB',(foto.width*2,foto.height));dupla.paste(foto,(0,0));dupla.paste(foto,(foto.width,0));foto=dupla
    elif tipo=='olhos':ImageDraw.Draw(foto).rectangle((40,65,155,95),fill='black')
    elif tipo=='boca':ImageDraw.Draw(foto).rectangle((40,102,155,155),fill='black')
    elif tipo=='sem_rosto':foto=Image.new('RGB',(400,400),'blue')
    elif tipo=='pequena':foto=foto.resize((100,100))
    saida=io.BytesIO();foto.save(saida,'JPEG');return saida.getvalue()


def test_recria_retrato_pequeno_sem_metadados():
    original=Image.open(ROSTO);out=io.BytesIO();exif=Image.Exif();exif[0x010e]='dado-privado';original.save(out,'JPEG',exif=exif)
    raw=preparar_foto(out.getvalue())
    assert len(raw)<=65536 and b'dado-privado' not in raw
    with Image.open(io.BytesIO(raw)) as foto:assert foto.size==(160,160) and foto.format=='JPEG' and not foto.getexif()


@pytest.mark.parametrize('tipo',['dois','olhos','boca','sem_rosto','pequena'])
def test_rejeita_fotos_sem_enquadramento(tipo):
    with pytest.raises(ValueError):preparar_foto(modificada(tipo))


@pytest.mark.parametrize('entrada',[None,'https://example.org/foto.jpg','data:image/svg+xml;base64,PHN2Zz4=',b'GIF89a',b'x'*(2*1024*1024+1)])
def test_rejeita_formatos_falsos_e_arquivo_grande(entrada):
    with pytest.raises(ValueError):preparar_foto(entrada)


def test_foto_autenticada_privada_substituicao_e_remocao(db):
    client=server.app.test_client();payload={'foto':uri(ROSTO.read_bytes()),'email':'b@aluno.cps.sp.gov.br'}
    assert client.post('/api/perfil/foto',json=payload).status_code==401
    res=client.post('/api/perfil/foto',headers=auth(),json=payload);assert res.status_code==200,res.json
    id=res.json['foto_id'];path='/api/perfil/foto/'+id
    assert scalar(db,'SELECT email FROM perfis_fotos')==EMAIL
    assert scalar(db,'SELECT octet_length(foto) FROM perfis_fotos')<65536
    assert client.get(path).status_code==401
    assert client.get(path,headers=auth('b@aluno.cps.sp.gov.br')).status_code==404
    own=client.get(path,headers=auth());assert own.status_code==200 and own.mimetype=='image/jpeg'
    assert 'no-store' in own.headers['Cache-Control']
    assert client.get(path,headers=ADMIN).data==own.data
    assert client.post('/api/secretaria/perfil',headers=auth(),json={'email':EMAIL}).status_code==403
    lookup=client.post('/api/secretaria/perfil',headers=ADMIN,json={'email':EMAIL});assert lookup.json['perfil']['foto_id']==id
    assert client.get('/api/perfil',headers=auth()).json['perfil']['foto_id']==id
    bad=client.post('/api/perfil/foto',headers=auth(),json={'foto':uri(modificada('sem_rosto'))});assert bad.status_code==400
    assert client.get(path,headers=auth()).status_code==200
    nextid=client.post('/api/perfil/foto',headers=auth(),json=payload).json['foto_id'];assert nextid!=id
    assert client.get(path,headers=auth()).status_code==404
    assert scalar(db,'SELECT count(*) FROM perfis_fotos')==1
    assert client.delete('/api/perfil/foto',headers=auth()).status_code==200
    assert client.get('/api/perfil/foto/'+nextid,headers=auth()).status_code==404
    assert client.get('/api/perfil',headers=auth()).json['perfil']['foto_id'] is None


def test_perfil_no_fluxo_de_retirada_e_sem_exposicao_publica(db):
    client=server.app.test_client();id=item(db)
    assert client.post('/api/secretaria/perfil',headers=ADMIN,json={'item_id':id}).json['perfil']['email']==EMAIL
    assert client.post('/api/secretaria/perfil',headers=auth(),json={'item_id':id}).status_code==403
    for body in [{},{'item_id':True},{'item_id':-1},{'item_id':2**70},{'email':[]}]:
        assert client.post('/api/secretaria/perfil',headers=ADMIN,json=body).status_code==400
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE itens SET status='ENTREGUE' WHERE id=%s",(id,))
    assert client.post('/api/secretaria/perfil',headers=ADMIN,json={'item_id':id}).status_code==404
    for endpoint in ['/api/catalogo','/api/itens']:
        assert 'foto_id' not in client.get(endpoint).get_data(as_text=True)


def test_permissao_professor_reavaliada_em_cada_consulta(db):
    client=server.app.test_client();teacher='docente@etec.sp.gov.br'
    with db() as co:
        with co.cursor() as c:
            c.execute("INSERT INTO alunos VALUES(%s,'Docente','PROFESSOR','hash')",(teacher,))
            c.execute("INSERT INTO professores_acesso(email,nome,status) VALUES(%s,'Docente','PENDENTE')",(teacher,))
    token=auth(teacher)
    assert client.post('/api/perfil/foto',headers=token,json={'foto':uri(ROSTO.read_bytes())}).status_code==200
    id=client.post('/api/perfil/foto',headers=auth(),json={'foto':uri(ROSTO.read_bytes())}).json['foto_id']
    assert client.get('/api/perfil/foto/'+id,headers=token).status_code==404
    for estado,status in [('APROVADO',200),('REVOGADO',404)]:
        with db() as co:
            with co.cursor() as c:c.execute('UPDATE professores_acesso SET status=%s WHERE email=%s',(estado,teacher))
        assert client.get('/api/perfil/foto/'+id,headers=token).status_code==status
        assert client.post('/api/secretaria/perfil',headers=token,json={'email':EMAIL}).status_code==(200 if estado=='APROVADO' else 403)


@pytest.fixture(params=['ativo','modular'])
def cadastro(request,db,monkeypatch):
    if request.param=='ativo':return server.app.test_client(),server
    monkeypatch.setattr(auth_module,'get_db_connection',db)
    app=Flask('auth-termos');app.register_blueprint(auth_module.auth_bp)
    return app.test_client(),auth_module


def dados_cadastro(db):
    email='novo@aluno.cps.sp.gov.br'
    with db() as co:
        with co.cursor() as c:c.execute('INSERT INTO codigos_auth(email,codigo,expiracao) VALUES(%s,%s,%s)',(email,__import__('services.autenticacao_service',fromlist=['resumo_codigo']).resumo_codigo(email,'cadastro','123456'),datetime.now()+timedelta(minutes=5)))
    return dict(email=email,nome='Aluno Novo',rm='12345',senha='Senha-local-de-teste-123!',codigo='123456',aceite_termos=True,versao_termos=VERSAO_TERMOS)


def test_termos_ausentes_falsos_e_antigos_nao_consomem_codigo(cadastro,db):
    client,_=cadastro;payload=dados_cadastro(db)
    for change in [{'aceite_termos':False},{'aceite_termos':'true'},{'aceite_termos':1},{'versao_termos':'antiga'},{'versao_termos':None}]:
        assert client.post('/api/auth/cadastrar',json={**payload,**change}).status_code==400
    sem_aceite=payload.copy();sem_aceite.pop('aceite_termos')
    assert client.post('/api/auth/cadastrar',json=sem_aceite).status_code==400
    assert scalar(db,'SELECT count(*) FROM codigos_auth')==1
    assert scalar(db,'SELECT count(*) FROM termos_aceites')==0
    assert scalar(db,'SELECT count(*) FROM alunos')==2


def test_cadastro_registra_versao_e_timestamp_junto_da_conta(cadastro,db):
    client,_=cadastro;payload=dados_cadastro(db)
    res=client.post('/api/auth/cadastrar',json=payload);assert res.status_code==200,res.json
    assert scalar(db,'SELECT versao FROM termos_aceites WHERE email=%s',(payload['email'],))==VERSAO_TERMOS
    assert scalar(db,'SELECT aceito_em IS NOT NULL FROM termos_aceites') is True
    assert scalar(db,'SELECT count(*) FROM codigos_auth')==0
    assert check_password_hash(scalar(db,'SELECT senha_hash FROM alunos WHERE email=%s',(payload['email'],)),payload['senha'])


def test_senha_vazia_no_cadastro_preserva_codigo_para_correcao(cadastro,db):
    client,_=cadastro;payload=dados_cadastro(db)
    res=client.post('/api/auth/cadastrar',json={**payload,'senha':'\u3000'*12})
    assert res.status_code==400 and 'apenas espaços' in res.json['message']
    assert scalar(db,'SELECT count(*) FROM alunos')==2
    assert scalar(db,'SELECT count(*) FROM termos_aceites')==0
    assert scalar(db,'SELECT tentativas FROM codigos_auth WHERE email=%s',(payload['email'],))==0
    assert client.post('/api/auth/cadastrar',json=payload).status_code==200


def test_falha_no_aceite_reverte_conta_e_preserva_codigo(cadastro,db,monkeypatch):
    client,_=cadastro;payload=dados_cadastro(db)
    def falhar(*args):raise RuntimeError('Falha simulada antes do aceite')
    monkeypatch.setattr('utils.perfis.registrar_aceite',falhar)
    assert client.post('/api/auth/cadastrar',json=payload).status_code==503
    assert scalar(db,'SELECT count(*) FROM alunos WHERE email=%s',(payload['email'],))==0
    assert scalar(db,'SELECT count(*) FROM codigos_auth')==1


def test_mesmo_texto_publico_e_modal_sem_exigir_login():
    client=server.app.test_client();doc=client.get('/termos');api=client.get('/api/termos')
    assert doc.status_code==api.status_code==200
    assert api.json['versao']==VERSAO_TERMOS
    assert api.json['secoes']==[dict(titulo=t,texto=p) for t,p in SECOES_TERMOS]
    for titulo,texto in SECOES_TERMOS:assert titulo in doc.get_data(as_text=True) and texto in doc.get_data(as_text=True)
