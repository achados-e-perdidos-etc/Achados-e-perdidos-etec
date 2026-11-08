"""Protocolo Web Push real com transporte interceptado, sem contato com provedores."""
import base64
import json
import os
from unittest.mock import MagicMock, patch

import http_ece
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from requests import Response

import server
from services import push_delivery as service


def encode(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def public(key):
    return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


@pytest.fixture
def configured(monkeypatch):
    key=ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setenv('VAPID_PRIVATE_KEY',encode(key.private_numbers().private_value.to_bytes(32,'big')))
    monkeypatch.setenv('VAPID_PUBLIC_KEY',encode(public(key)))
    monkeypatch.setenv('VAPID_CLAIMS_EMAIL','mailto:teste@example.org')
    monkeypatch.setitem(server.app.config,'PUSH_AUTOSTART',False)
    return key


def subscription():
    recipient=ec.generate_private_key(ec.SECP256R1());auth=os.urandom(16)
    return {'endpoint':'https://fcm.googleapis.com/push/teste','keys':{'auth':encode(auth),'p256dh':encode(public(recipient))}},recipient,auth


def response(status):
    result=Response();result.status_code=status;result._content=b''
    return result


def test_criptografia_vapid_payload_e_timeout_reais(configured):
    sub,recipient,auth=subscription();captured=[]
    def transport(self,request,**kwargs):
        captured.append((request,kwargs));return response(201)
    with patch('requests.sessions.Session.send',transport):
        assert service.enviar_assinatura(sub,{'title':'Teste de envio','body':'Abra o portal','url':'/'})=='enviada'
    request,options=captured[0]
    decoded=http_ece.decrypt(request.body,private_key=recipient,auth_secret=auth,version='aes128gcm')
    assert json.loads(decoded)['title']=='Teste de envio'
    assert b'Abra o portal' not in request.body
    assert request.headers['Content-Encoding']=='aes128gcm'
    assert int(request.headers['TTL'])==3600
    assert options['allow_redirects'] is False and options['timeout']==8
    authorization=request.headers['Authorization']
    assert authorization.startswith('vapid t=')
    token=authorization.split('t=',1)[1].split(',',1)[0].strip()
    claims=jwt.decode(token,configured.public_key(),algorithms=['ES256'],audience='https://fcm.googleapis.com')
    assert claims['sub']=='mailto:teste@example.org'
    assert 'email_aluno' not in json.loads(decoded)


@pytest.mark.parametrize('status,expected',[(200,'enviada'),(201,'enviada'),(202,'enviada'),(404,'expirada'),(410,'expirada'),
    (401,'repetir'),(403,'repetir'),(408,'repetir'),(429,'repetir'),(500,'repetir'),(503,'repetir'),(301,'descartar'),(400,'descartar'),(413,'descartar')])
def test_status_do_provedor_tem_tratamento_expresso(configured,status,expected):
    sub,_,_=subscription()
    with patch('requests.sessions.Session.send',return_value=response(status)):
        assert service.enviar_assinatura(sub,{'title':'Teste'})==expected


@pytest.mark.parametrize('endpoint',['https://example.org/push','https://localhost/push','https://127.0.0.1/push',
    'https://fcm.googleapis.com.attacker.invalid/push','http://fcm.googleapis.com/x','https://user:pass@fcm.googleapis.com/x'])
def test_destinos_arbitrarios_nao_recebem_requisicoes(configured,endpoint):
    sub,_,_=subscription();sub['endpoint']=endpoint
    with patch('requests.sessions.Session.send') as transport:
        assert service.enviar_assinatura(sub,{'title':'Teste'})=='descartar'
        transport.assert_not_called()


def test_timeout_nao_expoe_endpoint_e_fica_para_reenvio(configured,caplog):
    import requests
    sub,_,_=subscription()
    with patch('requests.sessions.Session.send',side_effect=requests.Timeout('endpoint e chave que não devem aparecer')):
        assert service.enviar_assinatura(sub,{'title':'Teste'})=='repetir'
    assert 'não devem aparecer' not in caplog.text


@pytest.mark.parametrize('change',[('VAPID_PUBLIC_KEY','invalida'),('VAPID_PRIVATE_KEY',''),('VAPID_PRIVATE_KEY','invalida'),('VAPID_CLAIMS_EMAIL','javascript:teste')])
def test_configuracao_invalida_desabilita_sem_usar_valor_de_exemplo(configured,monkeypatch,change):
    monkeypatch.setenv(*change)
    assert service.chave_publica()==''
    with patch.object(service,'get_db_connection') as db:
        assert service.enfileirar('aluno@aluno.cps.sp.gov.br','chat')==0
        db.assert_not_called()


def test_chave_publica_so_e_anunciada_quando_corresponde_a_privada(configured):
    result=server.app.test_client().get('/api/push/public-key')
    assert result.json['success'] and result.json['habilitado']
    assert result.json['publicKey']==encode(public(configured))
    assert 'private' not in result.get_data(as_text=True).lower()


@pytest.mark.parametrize('emails',[[],[('um@aluno.cps.sp.gov.br',)],[('um@aluno.cps.sp.gov.br',),('dois@aluno.cps.sp.gov.br',)]])
def test_chat_somente_notifica_autoria_autenticada_inequivoca(configured,emails):
    conn=MagicMock();conn.cursor.return_value.fetchall.return_value=emails
    with patch.object(service,'get_db_connection',return_value=conn),patch.object(service,'notificar',return_value=1) as notify:
        service.notificar_resposta('12345')
    if len(emails)==1:notify.assert_called_once_with('um@aluno.cps.sp.gov.br','chat')
    else:notify.assert_not_called()
    assert 'm.email_aluno' in conn.cursor.return_value.execute.call_args.args[0]


def test_fila_ignora_assinatura_removida_ou_vinculada_a_outra_conta(configured):
    job={'id':1,'tentativas':1,'subscription_json':'{}','payload_json':'{}'}
    with patch.object(service,'_proxima',side_effect=[job,None]),patch.object(service,'_assinatura_atual',return_value=False),\
         patch.object(service,'enviar_assinatura') as send,patch.object(service,'_concluir') as done:
        assert service.processar_pendentes()==1
    send.assert_not_called();done.assert_called_once_with(job,'descartar')


@pytest.mark.parametrize('result,code',[('enfileirado',202),('limite',429),('sem_dispositivo',400),('desabilitado',503)])
@pytest.mark.parametrize('implementation',['unificado','modular'])
def test_api_de_teste_sempre_usa_conta_autenticada(configured,result,code,implementation):
    app=server.app
    if implementation=='modular':
        from flask import Flask
        from blueprints.Push import push_bp
        app=Flask(__name__);app.register_blueprint(push_bp);app.config['PUSH_AUTOSTART']=False
    server.limiter.enabled=False
    headers={'Authorization':'Bearer '+server.gerar_token_aluno('aluno@aluno.cps.sp.gov.br','Aluno','12345')}
    with patch.object(service,'enfileirar_teste',return_value=result) as queue:
        client=app.test_client()
        assert client.post('/api/push/test').status_code==401
        response=client.post('/api/push/test',headers=headers,json={'email':'outro@aluno.cps.sp.gov.br','rm':'99999'})
        assert response.status_code==code
        queue.assert_called_once_with('aluno@aluno.cps.sp.gov.br')
        if code==202:assert response.json['queued'] is True
