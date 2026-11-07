import hashlib,io
from unittest.mock import patch
import pytest
from PIL import Image
from tests.test_push_delivery_postgres import postgres,db_env
from tests.test_push_delivery import configured
from tests.test_portal_updates_postgres import db,auth
from blueprints import uploads
import server

@pytest.fixture
def client(db,monkeypatch):
    monkeypatch.setattr(uploads,'get_db_connection',db)
    return server.app.test_client()

def foto():
    out=io.BytesIO();Image.new('RGB',(200,200),'blue').save(out,format='PNG');return out.getvalue()

def iniciar(client,data):
    res=client.post('/api/uploads',headers=auth(),json={'sha256':hashlib.sha256(data).hexdigest(),'tamanho':len(data)})
    assert res.status_code==201;return '/api/uploads/'+res.json['id']

def test_retomar_offset_e_finalizacao_sem_reenviar(client):
    data=foto();path=iniciar(client,data);parte=len(data)//2
    assert client.put(path,headers={**auth(),'X-Upload-Offset':'0'},data=data[:parte]).status_code==200
    assert client.put(path,headers={**auth(),'X-Upload-Offset':'0'},data=data[:parte]).status_code==409
    assert client.get(path,headers=auth()).json['recebidos']==parte
    assert client.put(path,headers={**auth(),'X-Upload-Offset':str(parte)},data=data[parte:]).status_code==200
    with patch.object(uploads.cloudinary.uploader,'upload',side_effect=RuntimeError('credencial privada')):
        r=client.post(path+'/finalizar',headers=auth());assert r.status_code==503
        assert 'credencial' not in r.get_data(as_text=True)
    assert client.get(path,headers=auth()).json['recebidos']==len(data)
    with patch.object(uploads.cloudinary.uploader,'upload',return_value={'secure_url':'https://imagem.invalid/pronta.png'}) as send:
        for _ in range(2):assert client.post(path+'/finalizar',headers=auth()).json['url']=='https://imagem.invalid/pronta.png'
        assert send.call_count==1

def test_arquivos_independentes_e_contas_isoladas(client):
    data=foto();a=iniciar(client,data);b=iniciar(client,data)
    assert client.put(a,headers={**auth(),'X-Upload-Offset':'0'},data=data[:2]).status_code==200
    assert client.put(b,headers={**auth(),'X-Upload-Offset':'0'},data=data).status_code==200
    assert client.get(a,headers=auth('b@aluno.cps.sp.gov.br')).status_code==404
    assert client.get(a).status_code==401
    assert client.get(b,headers=auth()).json['recebidos']==len(data)
    assert client.get(a,headers=auth()).json['recebidos']==2

def test_remover_envio_libera_partes_e_nao_remove_de_outros(client,db):
    data=foto();path=iniciar(client,data)
    assert client.put(path,headers={**auth(),'X-Upload-Offset':'0'},data=data).status_code==200
    assert client.delete(path,headers=auth('b@aluno.cps.sp.gov.br')).status_code==404
    assert client.delete(path,headers=auth()).status_code==200
    with db() as co:
        with co.cursor() as c:c.execute('SELECT count(*) FROM uploads_partes');assert c.fetchone()[0]==0

def test_limite_de_arquivos_pendentes(client):
    data=foto()
    for _ in range(4):iniciar(client,data)
    assert client.post('/api/uploads',headers=auth(),json={'tamanho':len(data),'sha256':hashlib.sha256(data).hexdigest()}).status_code==429

def test_reselecionar_mesma_foto_recupera_sessao_confirmada(client):
    data=foto();path=iniciar(client,data)
    assert client.post(path+'/parte',headers={**auth(),'X-Upload-Offset':'0'},data=data[:10]).status_code==200
    res=client.post('/api/uploads',headers=auth(),json={'tamanho':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retomar':True})
    assert res.status_code==200
    assert path.endswith(res.json['id']) and res.json['recebidos']==10
