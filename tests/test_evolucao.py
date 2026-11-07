"""Contratos de segurança e transações em PostgreSQL isolado."""
import base64,io,uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import pytest
from PIL import Image,ImageDraw
import jwt
import server
from config import JWT_SECRET
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from blueprints import evolucao
from services import cloudinary_service,matches_service,professores_service,notificacoes_service
from utils.imagens import preparar_imagem
from utils.evolucao import contextualizar


def auth(email='a@aluno.cps.sp.gov.br',admin=False):
    token=server.gerar_token_secretaria(email) if admin else server.gerar_token_aluno(email,'Aluno','12345')
    return {'Authorization':'Bearer '+token}


def foto(cor='blue',size=(40,40),fmt='PNG'):
    out=io.BytesIO();image=Image.new('RGB',size,cor)
    ImageDraw.Draw(image).line((4,4,size[0]-4,size[1]-4),fill='black',width=3)
    image.save(out,format=fmt)
    return 'data:image/'+('jpeg' if fmt=='JPEG' else fmt.lower())+';base64,'+base64.b64encode(out.getvalue()).decode()


@pytest.fixture
def db(db_env,monkeypatch):
    for mod in [evolucao,matches_service,professores_service,notificacoes_service]:monkeypatch.setattr(mod,'get_db_connection',db_env)
    monkeypatch.setattr(server,'get_db_connection',lambda:contextualizar(db_env()))
    return db_env


def item(db,email='a@aluno.cps.sp.gov.br',status='SOLICITADO',aprovado=True):
    with db() as co:
        with co.cursor() as c:
            c.execute('''INSERT INTO itens(nome_item,descricao,categoria,data_encontrado,local_encontrado,status,
              aprovado,solicitado_por,rm_aluno,email_solicitante)
              VALUES('Calculadora Casio azul','Calculadora científica Casio azul','ESCOLARES','01/11/2026','Pátio',%s,%s,'Aluno','12345',%s) RETURNING id''',(status,aprovado,email))
            return c.fetchone()[0]


def codigo(client,id):
    res=client.post(f'/api/retiradas/{id}/codigo',headers=auth(),json={});assert res.status_code==200,res.json
    return res.json['codigo']


def confirmar(client,id,code,**change):
    data=dict(codigo=code,requisicao=str(uuid.uuid4()),identidade_conferida=True,assinatura=foto('white',(700,180)))
    data.update(change)
    return client.post(f'/api/retiradas/{id}/confirmar',headers=auth('secretaria@etec.sp.gov.br',True),json=data)


def test_codigo_privado_vinculado_ao_item_e_reutilizavel_ate_expirar(db):
    client=server.app.test_client();id=item(db)
    first=codigo(client,id);assert len(first)==6 and first.isascii() and first.isdigit()
    assert codigo(client,id)==first
    assert client.post(f'/api/retiradas/{id}/codigo',headers=auth('b@aluno.cps.sp.gov.br')).status_code==404
    assert client.post(f'/api/retiradas/{id}/codigo').status_code==401
    assert scalar(db,'SELECT nonce::text FROM retiradas_codigos')!=first


def test_cinco_erros_bloqueiam_codigo_ate_expirar(db):
    client=server.app.test_client();id=item(db);code=codigo(client,id)
    wrong='000000' if code!='000000' else '000001'
    for _ in range(5):assert confirmar(client,id,wrong).status_code==409
    assert confirmar(client,id,code).status_code==409
    assert client.post(f'/api/retiradas/{id}/codigo',headers=auth()).status_code==429
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE retiradas_codigos SET expira_em=CURRENT_TIMESTAMP-INTERVAL '1 second'")
    codigo(client,id)
    assert scalar(db,'SELECT tentativas FROM retiradas_codigos')==0


def test_entrega_atomica_assinatura_privada_auditoria_e_idempotencia(db):
    client=server.app.test_client();id=item(db);code=codigo(client,id);key=str(uuid.uuid4())
    result=confirmar(client,id,code,requisicao=key);assert result.status_code==200,result.json
    assert confirmar(client,id,code,requisicao=key).json['repetida'] is True
    assert confirmar(client,id,code).status_code==409
    assert scalar(db,'SELECT count(*) FROM entregues')==1
    assert scalar(db,'SELECT status FROM itens WHERE id=%s',(id,))=='ENTREGUE'
    assert scalar(db,'SELECT metodo FROM entregues')=='CODIGO'
    response=client.get('/api/entregues',headers=auth('secretaria@etec.sp.gov.br',True))
    assert 'assinatura' not in response.json[0]
    signature=client.get(f"/api/retiradas/comprovantes/{result.json['comprovante_id']}/assinatura",headers=auth('secretaria@etec.sp.gov.br',True))
    assert signature.status_code==200 and signature.mimetype=='image/jpeg'
    assert 'no-store' in signature.headers['Cache-Control']
    assert client.get(f"/api/retiradas/comprovantes/{result.json['comprovante_id']}/assinatura",headers=auth()).status_code==403
    rows=client.get(f'/api/itens/{id}/ocorrencias',headers=auth('secretaria@etec.sp.gov.br',True)).json['ocorrencias']
    assert rows[0]['ator_id']=='secretaria@etec.sp.gov.br'
    assert rows[0]['anterior']['status']=='SOLICITADO' and rows[0]['atual']['status']=='ENTREGUE'
    assert client.get(f'/api/itens/{id}/ocorrencias',headers=auth()).status_code==403


def test_dois_atendentes_nao_entregam_duas_vezes(db):
    id=item(db);code=codigo(server.app.test_client(),id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:confirmar(server.app.test_client(),id,code).status_code,range(2)))
    assert sorted(statuses)==[200,409]
    assert scalar(db,'SELECT count(*) FROM entregues')==1


def test_codigo_nao_libera_item_revertido_e_aluno_nao_entrega(db):
    client=server.app.test_client();id=item(db);code=codigo(client,id)
    assert client.post(f'/api/retiradas/{id}/confirmar',headers=auth(),json={}).status_code==403
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE itens SET status='DISPONÍVEL',email_solicitante=NULL WHERE id=%s",(id,))
    assert confirmar(client,id,code).status_code==409
    assert scalar(db,'SELECT count(*) FROM entregues')==0


def test_auditoria_preservada_apos_excluir_e_rollback_nao_cria_evento(db):
    id=item(db)
    co=db();c=co.cursor();c.execute("UPDATE itens SET status='ENTREGUE' WHERE id=%s",(id,));co.rollback();co.close()
    assert scalar(db,'SELECT count(*) FROM ocorrencias_itens')==1
    client=server.app.test_client()
    assert client.delete(f'/api/itens/{id}',headers=auth('secretaria@etec.sp.gov.br',True)).status_code==200
    assert scalar(db,'SELECT count(*) FROM ocorrencias_itens')==2
    assert scalar(db,'SELECT ator_id FROM ocorrencias_itens ORDER BY id DESC LIMIT 1')=='secretaria@etec.sp.gov.br'
    with pytest.raises(Exception):
        with db() as co:
            with co.cursor() as c:c.execute('DELETE FROM ocorrencias_itens')


def test_perfis_distintos_e_revogacao_imediata_de_moderador(db):
    client=server.app.test_client();teacher='docente@etec.sp.gov.br'
    with db() as co:
        with co.cursor() as c:
            c.execute("INSERT INTO alunos VALUES(%s,'Docente','PROFESSOR','hash')",(teacher,))
            c.execute("INSERT INTO professores_acesso(email,nome,status) VALUES(%s,'Docente','APROVADO')",(teacher,))
    for headers,perfil in [(auth(),'aluno'),(auth('secretaria@etec.sp.gov.br',True),'administrador_geral'),(auth(teacher),'moderador')]:
        res=client.get('/api/auth/verificar',headers=headers);assert res.json['user']['perfil']==perfil
    assert client.get('/api/secretaria/professores',headers=auth(teacher)).status_code==403
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE professores_acesso SET status='REVOGADO' WHERE email=%s",(teacher,))
    assert client.get('/api/itens/1/ocorrencias',headers=auth(teacher)).status_code==403


@pytest.mark.parametrize('tipo',['encontrado','mural'])
def test_sincronizacao_repete_sem_duplicar_e_isola_contas(db,tipo):
    client=server.app.test_client();key=str(uuid.uuid4());path='/api/mural' if tipo=='mural' else '/api/itens/cadastrar-aluno'
    data={'nome':'Estojo azul','categoria':'OUTROS','descricao':'Estojo com zíper','fotos':[]}
    for _ in range(2):
        result=client.post(path,headers={**auth(),'Idempotency-Key':key},json=data);assert result.status_code==200,result.json
    table='itens' if tipo=='encontrado' else 'mural_perdidos'
    assert scalar(db,'SELECT count(*) FROM '+table)==1
    assert client.post(path,headers={**auth(),'Idempotency-Key':key},json={**data,'descricao':'Outro objeto'}).status_code==409
    assert client.post(path,headers={**auth('b@aluno.cps.sp.gov.br'),'Idempotency-Key':key},json=data).status_code==200
    assert scalar(db,'SELECT count(*) FROM '+table)==2


def test_match_apenas_publicados_deduplicado_sem_ia_e_central_sem_push(db,monkeypatch):
    monkeypatch.setattr('services.push_delivery.configuracao',lambda:None)
    with db() as co:
        with co.cursor() as c:
            for descricao in ['calculadora Casio azul','calculadora Casio azul','azul']:
                c.execute("INSERT INTO mural_perdidos VALUES(DEFAULT,'Aluno','12345','a@aluno.cps.sp.gov.br','ESCOLARES',%s,'01/11/2026','PROCURANDO')",(descricao,))
    id=item(db,status='DISPONÍVEL',aprovado=False)
    assert matches_service.processar(db)==0
    with db() as co:
        with co.cursor() as c:c.execute('UPDATE itens SET aprovado=TRUE WHERE id=%s',(id,))
    assert matches_service.processar(db)==1
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE itens SET local_encontrado='Outro armário' WHERE id=%s",(id,))
    assert matches_service.processar(db)==0
    assert scalar(db,"SELECT count(*) FROM notificacoes WHERE evento='match'")==1


@pytest.mark.parametrize('entrada',['data:image/png;base64,'+base64.b64encode(b'<script>bad</script>').decode(),'http://127.0.0.1/segredo','data:image/svg+xml;base64,PHN2Zz4=','arquivo.exe'])
def test_arquivo_invalido_nunca_chega_ao_provedor(entrada):
    with patch.object(cloudinary_service.cloudinary.uploader,'upload') as upload:
        with pytest.raises(cloudinary_service.FalhaUploadFotos):cloudinary_service.processar_fotos([entrada])
        upload.assert_not_called()


def test_imagem_redimensionada_e_recriada_com_nome_anonimo():
    clean=preparar_imagem(foto(size=(2400,1600)))
    with Image.open(io.BytesIO(clean)) as image:
        assert max(image.size)<=1600 and image.format=='JPEG' and not image.getexif()
    with patch.object(cloudinary_service.cloudinary.uploader,'upload',return_value={'secure_url':'https://res.cloudinary.com/test/image/upload/etec_achados/anon.jpg'}) as upload:
        cloudinary_service.processar_fotos([foto()])
        uuid.UUID(upload.call_args.kwargs['public_id'].split('/')[-1])
        assert upload.call_args.kwargs['resource_type']=='image'


def test_limite_de_pixels_rejeitado_antes_de_upload():
    with pytest.raises(ValueError):preparar_imagem(foto(size=(5000,4000)))


def test_api_nao_aceita_jwt_em_url_nem_token_sem_expiracao():
    client=server.app.test_client();token=server.gerar_token_aluno('a@aluno.cps.sp.gov.br','Aluno','12345')
    assert client.get('/api/auth/verificar?token='+token).status_code==401
    invalid=jwt.encode({'email':'a@aluno.cps.sp.gov.br','role':'aluno','auth_version':2},JWT_SECRET,algorithm='HS256')
    assert client.get('/api/auth/verificar',headers={'Authorization':'Bearer '+invalid}).status_code==401


@pytest.mark.parametrize('path',['/server.py','/.git/config','/config.py','/tests/test_evolucao.py','/requirements.txt'])
def test_codigo_e_arquivos_internos_nao_sao_publicados(path):
    assert server.app.test_client().get(path).status_code==404
