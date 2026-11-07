"""Mesmas regras e documentos, protocolos reais e privacidade dos painéis."""
import base64,io,queue,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest,requests
from PIL import Image
from tests.test_push_delivery_postgres import postgres,db_env,scalar
from tests.test_push_delivery import configured
from tests.test_evolucao import db,auth,item,codigo,confirmar
from tests.test_catalogo_moderacao import inserir
from blueprints import uploads
from services import cloudinary_service
from utils.ferramentas import id_etiqueta,filtrar_itens
from desktop_camera import ler_qr_arquivo
from desktop_uploads import UploadsDesktop
from desktop_formulario import compactar_arquivo
import server

ADMIN=auth('secretaria@etec.sp.gov.br',True)


def test_documentos_comuns_privados_filtros_e_html_escapado(db):
    nome='Óculos <script>alert(1)</script>'
    id=inserir(db,nome=nome,categoria='ACESSÓRIOS',data='06/11/2026',local='Pátio')
    inserir(db,nome='Outro',local='Sala');client=server.app.test_client()
    url='/api/secretaria/documentos?tipo=COMPLETO&categoria=ACESS%C3%93RIOS&local=patio&inicio=2026-11-01&fim=2026-11-07'
    assert client.get(url).status_code==401 and client.get(url,headers=auth()).status_code==403
    res=client.get(url,headers=ADMIN);assert res.status_code==200,res.json
    dados=res.json;assert dados['total']==1 and dados['linhas'][0][0]==id and dados['linhas'][0][1]==nome
    assert '<script>alert(1)' not in dados['html'] and '&lt;script&gt;' in dados['html']
    assert 'no-store' in res.headers['Cache-Control']
    for query in ['tipo=INVALIDO','inicio=2026-02-31','inicio=2026-11-07&fim=2026-11-01']:
        assert client.get('/api/secretaria/documentos?'+query,headers=ADMIN).status_code==400


@pytest.mark.parametrize('tipo',['INVENTARIO','ENTREGAS','DOACOES','COMPLETO'])
def test_tipos_de_relatorio_nao_confundem_estoque_entregas_e_doacoes(db,tipo):
    inserir(db,nome='Disponível');inserir(db,nome='Doação')
    with db() as co:
        with co.cursor() as c:c.execute("UPDATE itens SET status='PARA DOAÇÃO' WHERE nome_item='Doação'")
    id=item(db);client=server.app.test_client();r=confirmar(client,id,codigo(client,id));assert r.status_code==200
    result=client.get('/api/secretaria/documentos?tipo='+tipo,headers=ADMIN).json
    expected={'INVENTARIO':1,'ENTREGAS':1,'DOACOES':1,'COMPLETO':3}[tipo]
    assert result['total']==expected
    if tipo=='ENTREGAS':assert result['linhas'][0][2]=='Calculadora Casio azul'


def test_etiquetas_completas_em_varias_paginas_png_e_leitura_qr_real(db,tmp_path):
    ids=[inserir(db,nome='Objeto '+str(i)) for i in range(16)];client=server.app.test_client()
    res=client.get('/api/secretaria/documentos?tipo=ETIQUETAS',headers=ADMIN)
    assert res.status_code==200,res.json
    assert res.json['total']==16 and res.json['html'].count('<section class="folha">')==2
    for id in ids:assert f'Objeto #{id}<' in res.json['html']
    png=client.get(f'/api/secretaria/etiquetas/{ids[0]}.png',headers=ADMIN)
    file=tmp_path/'qr.png';file.write_bytes(png.data)
    assert ler_qr_arquivo(file)=='ETEC-ITEM-'+str(ids[0])
    assert id_etiqueta(ler_qr_arquivo(file))==ids[0]
    for page in [1,2]:
        response=client.get('/api/secretaria/etiquetas.png?pagina='+str(page),headers=ADMIN)
        assert response.status_code==200
        with Image.open(io.BytesIO(response.data)) as img:assert img.size==(1240,1754)
    assert client.get('/api/secretaria/etiquetas.png?pagina=3',headers=ADMIN).status_code==400
    assert client.get(f'/api/secretaria/etiquetas/{ids[0]}.png',headers=auth()).status_code==403


@pytest.mark.parametrize('valor',['https://site/ETEC-ITEM-7','x7','ETEC-ITEM-0','-1','2147483648','ETEC-ITEM-7<script>'])
def test_qr_invalido_nao_abre_objeto_por_numeros_arbitrarios(valor):
    with pytest.raises(ValueError):id_etiqueta(valor)


def test_filtros_do_estoque_sem_acentos_datas_e_intervalo():
    rows=[dict(id=1,nome='Óculos',txt_local='Pátio',txt_data='06/11/2026',categoria='ACESSÓRIOS'),dict(id=2,nome='Óculos',txt_local='Pátio',txt_data='legado inválido',categoria='ACESSÓRIOS')]
    filtros={'q':'oculos','local':'patio','categoria':'acessorios','inicio':'2026-11-01','fim':'2026-11-07'}
    assert [i['id'] for i in filtrar_itens(rows,filtros)]==[1]


def test_upload_desktop_independente_retoma_resposta_perdida_sem_reenviar_foto_pronta(db,monkeypatch,tmp_path):
    monkeypatch.setattr(uploads,'get_db_connection',db)
    monkeypatch.setattr(cloudinary_service,'CLOUDINARY_CLOUD_NAME','teste')
    monkeypatch.setattr(cloudinary_service.cloudinary.uploader,'upload',lambda *a,**kw:{'secure_url':'https://res.cloudinary.com/teste/image/upload/'+kw['public_id']+'.jpg'})
    api=server.app.test_client();falhou={'sim':False};contagens={}
    def chamar(method,path,**kwargs):
        response=server.app.test_client().open(path,method=method,headers=kwargs.get('headers'),data=kwargs.get('data'),json=kwargs.get('json'))
        if path.endswith('/parte'):
            contagens[path]=contagens.get(path,0)+1
            if not falhou['sim'] and response.status_code==200:falhou['sim']=True;raise requests.Timeout('Resposta perdida após gravar parte')
        if response.status_code>=400:
            res=requests.Response();res.status_code=response.status_code;res._content=response.data
            raise requests.HTTPError('Envio interrompido',response=res)
        return SimpleNamespace(json=lambda:response.json)
    engine=object.__new__(UploadsDesktop);engine.dono=SimpleNamespace(chamar_api=chamar);engine.headers=ADMIN;engine.fechado=threading.Event();engine.fila=queue.Queue();engine.pool=ThreadPoolExecutor(max_workers=4)
    engine.items=[]
    for cor in ['red','blue']:
        file=tmp_path/(cor+'.png');Image.new('RGB',(500,500),cor).save(file)
        foto=compactar_arquivo(file);engine.items.append(dict(foto=foto,id=None,offset=0,url=None,future=None,erro=None,cancelado=False))
    try:
        with pytest.raises(ValueError,match='Tentar novamente'):engine.enviar_todas()
        assert sum(bool(i['url']) for i in engine.items)==1
        id_pronta=next(i['id'] for i in engine.items if i['url']);antes=contagens['/api/uploads/'+id_pronta+'/parte']
        urls=engine.enviar_todas();assert len(urls)==2 and all(u.startswith('https://') for u in urls)
        assert contagens['/api/uploads/'+id_pronta+'/parte']==antes
        assert scalar(db,'SELECT count(*) FROM uploads_fotos WHERE url IS NOT NULL')==2
        assert scalar(db,'SELECT count(*) FROM uploads_partes')==0
    finally:engine.fechado.set();engine.pool.shutdown(wait=True)
