"""Falhas do provedor não viram sucesso ou gravação de item sem fotos."""
from unittest.mock import MagicMock, patch
import pytest
import server
from services import cloudinary_service as service


def test_unificado_usa_processamento_canonico():
    assert server.processar_fotos is service.processar_fotos


def test_urls_existentes_e_sem_fotos_nao_fazem_upload():
    with patch.object(service.cloudinary.uploader,'upload') as upload:
        assert service.processar_fotos([])==[]
        assert service.processar_fotos(['https://img.example.org/a.jpg'])==['https://img.example.org/a.jpg']
        upload.assert_not_called()


def test_ordem_das_fotos_e_preservada():
    with patch.object(service.cloudinary.uploader,'upload',side_effect=[{'secure_url':'https://img.example.org/a.jpg'},{'secure_url':'https://img.example.org/b.jpg'}]):
        assert service.processar_fotos(['foto-a','foto-b'])==['https://img.example.org/a.jpg','https://img.example.org/b.jpg']


@pytest.mark.parametrize('bad',[[],{}, {'secure_url':''},{'secure_url':'http://img.example.org/a.jpg'}])
def test_resposta_incompleta_nao_perde_foto_silenciosamente(bad):
    with patch.object(service.cloudinary.uploader,'upload',return_value=bad):
        with pytest.raises(service.FalhaUploadFotos):service.processar_fotos(['foto'])


@pytest.mark.parametrize('implementation',['unificado','modular'])
@pytest.mark.parametrize('path,admin',[('/api/itens/cadastrar-aluno',False),('/api/itens',True),('/api/itens/1',True)])
def test_falha_do_provedor_nao_grava_no_banco_nem_expoe_erro(implementation,path,admin):
    app=server.app;module=server
    if implementation=='modular':
        from flask import Flask
        from blueprints import itens
        app=Flask(__name__);app.register_blueprint(itens.itens_bp);module=itens
    app.config['TESTING']=True;server.limiter.enabled=False
    token=server.gerar_token_secretaria('secretaria@etec.sp.gov.br') if admin else server.gerar_token_aluno('aluno@aluno.cps.sp.gov.br','Aluno','12345')
    # Primeiro arquivo sobe; a falha do segundo ainda deve impedir gravação do item.
    with patch.object(module,'get_db_connection') as db,patch.object(service.cloudinary.uploader,'upload',side_effect=[{'secure_url':'https://img.example.org/a.jpg'},RuntimeError('credencial privada do provedor')]):
        db.return_value.cursor.return_value.fetchone.return_value={'id':1,'nome_item':'Estojo','descricao':'Descrição','status':'DISPONÍVEL'}
        result=app.test_client().open(path,method='PUT' if path.endswith('/1') else 'POST',headers={'Authorization':'Bearer '+token},json={'nome':'Estojo','descricao':'Descrição','fotos':['foto-a','foto-b']})
        assert result.status_code==502,result.json
        assert result.json['success'] is False
        assert 'credencial privada' not in result.get_data(as_text=True)
        if path.endswith('/1'):
            assert not any('UPDATE ' in call.args[0] for call in db.return_value.cursor.return_value.execute.call_args_list)
            db.return_value.rollback.assert_called_once()
        else:
            db.assert_not_called()


@pytest.mark.parametrize('implementation',['unificado','modular'])
@pytest.mark.parametrize('photos,expected',[(None,'https://img.example.org/antiga.jpg'),([],''),(['foto-nova'],'https://img.example.org/nova.jpg')])
def test_edicao_persiste_fotos_e_omissao_preserva_anteriores(implementation,photos,expected):
    import sqlite3,json
    from tests.test_student_authorship import Connection
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE itens(id INTEGER PRIMARY KEY,nome_item TEXT,descricao TEXT,categoria TEXT,data_encontrado TEXT,local_encontrado TEXT,status TEXT,aprovado BOOLEAN,foto TEXT,fotos_json TEXT);
        INSERT INTO itens VALUES(1,'Estojo','Descrição','OUTROS','01/11/2026','Pátio','DISPONÍVEL',TRUE,'https://img.example.org/antiga.jpg','["https://img.example.org/antiga.jpg"]');''')
    app=server.app;module=server
    if implementation=='modular':
        from flask import Flask
        from blueprints import itens
        app=Flask(__name__);app.register_blueprint(itens.itens_bp);module=itens
    app.config['TESTING']=True;server.limiter.enabled=False
    payload={'nome':'Estojo atualizado'}
    if photos is not None:payload['fotos']=photos
    try:
        with patch.object(module,'get_db_connection',return_value=Connection(db)),patch.object(service.cloudinary.uploader,'upload',return_value={'secure_url':'https://img.example.org/nova.jpg'}):
            result=app.test_client().put('/api/itens/1',headers={'Authorization':'Bearer '+server.gerar_token_secretaria('secretaria@etec.sp.gov.br')},json=payload)
            assert result.status_code==200,result.json
            row=db.execute('SELECT * FROM itens').fetchone()
            assert row['nome_item']=='Estojo atualizado'
            assert row['foto']==expected
            assert json.loads(row['fotos_json'])==([expected] if expected else [])
    finally:db.close()
