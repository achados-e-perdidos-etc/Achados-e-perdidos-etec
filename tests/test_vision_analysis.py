"""Contratos da análise visual sem rede, banco ou credenciais de terceiros."""
import base64
import io
import json
from unittest.mock import Mock

import pytest
import requests
from PIL import Image

import server
from services import ai_vision_service as vision


@pytest.fixture
def image_data():
    image = Image.new('RGB', (24, 24), color=(30, 80, 190))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(vision, 'GEMINI_API_KEY', 'chave-ficticia-dos-testes')
    post = Mock()
    monkeypatch.setattr(vision.requests, 'post', post)
    return post


def model_result(**changes):
    result = {
        'nome': 'Caderno espiral',
        'descricao': 'Caderno com capa azul e espiral preta na lateral.',
        'categoria': 'ESCOLARES',
        'cores': ['azul', 'preto'],
        'tags': ['caderno', 'espiral'],
        'confianca_objeto': 'alta',
        'alternativas': [],
        'objetos_detectados': ['caderno'],
        'ocr_texto': '',
        'ocr_nome_aluno': '',
        'ocr_rm': '',
        'ocr_serie': '',
        'tipo_documento': '',
        'ocr_confianca': 'baixa',
    }
    result.update(changes)
    return result


def provider_response(result):
    response = Mock(status_code=200)
    response.json.return_value = {
        'candidates': [{
            'content': {'parts': [{'text': json.dumps(result, ensure_ascii=False)}]},
            'finishReason': 'STOP',
        }],
    }
    return response


def assert_manual_only(result, error):
    assert error is None
    assert result['pode_preencher'] is False
    assert result['confianca_objeto'] == 'baixa'
    assert result.get('aviso')


def test_sem_chave_nao_chama_provedor_nem_simula_identificacao(image_data, provider, monkeypatch):
    monkeypatch.setattr(vision, 'GEMINI_API_KEY', '')
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert_manual_only(result, error)
    assert result['metodo'] != 'gemini_vision_ocr'
    provider.assert_not_called()


@pytest.mark.parametrize('status', [401, 403, 404, 429, 500, 503])
def test_falhas_http_nao_preenchem_formulario(status, image_data, provider):
    provider.return_value = Mock(status_code=status)
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert_manual_only(result, error)
    provider.assert_called_once()


def test_timeout_nao_preenche_formulario(image_data, provider):
    provider.side_effect = requests.Timeout('tempo esgotado')
    assert_manual_only(*vision.analisar_imagem_com_ia(image_data))


@pytest.mark.parametrize('provider_json', [
    {},
    {'candidates': []},
    {'candidates': [{'content': {'parts': [{'text': '{json incompleto'}]}}]},
    {'candidates': [{'content': {'parts': [{'text': '[]'}]}}]},
])
def test_resposta_invalida_nao_preenche_formulario(provider_json, image_data, provider):
    response = Mock(status_code=200)
    response.json.return_value = provider_json
    provider.return_value = response
    assert_manual_only(*vision.analisar_imagem_com_ia(image_data))


@pytest.mark.parametrize('invalid_image', [
    'isto-nao-e-base64',
    'data:image/png;base64,%%%invalido%%%',
    'data:image/png;base64,' + base64.b64encode(b'isto nao e uma imagem').decode(),
])
def test_bytes_invalidos_sao_rejeitados_antes_de_chamar_ia(invalid_image, provider):
    result, error = vision.analisar_imagem_com_ia(invalid_image)
    assert result is None
    assert error
    provider.assert_not_called()


@pytest.mark.parametrize('confidence', ['alta', 'media'])
def test_resultado_completo_e_confianca_permitida_libera_preenchimento(confidence, image_data, provider):
    provider.return_value = provider_response(model_result(confianca_objeto=confidence))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is True
    assert result['metodo'] == 'gemini_vision_ocr'
    assert result['nome'] == 'Caderno espiral'
    assert result['descricao'] == 'Caderno com capa azul e espiral preta na lateral.'
    payload = provider.call_args.kwargs['json']
    assert payload['contents'][0]['parts'][1]['inline_data']['mime_type'] == 'image/png'


@pytest.mark.parametrize('confidence', ['baixa', '', None, 'certeza-absoluta'])
def test_confianca_baixa_ausente_ou_invalida_nao_libera_preenchimento(confidence, image_data, provider):
    provider.return_value = provider_response(model_result(confianca_objeto=confidence))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is False


@pytest.mark.parametrize('changes', [{'nome': ''}, {'descricao': ''}, {'nome': None}, {'descricao': None}])
def test_identificacao_incompleta_nao_libera_preenchimento(changes, image_data, provider):
    provider.return_value = provider_response(model_result(**changes))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is False


@pytest.mark.parametrize('finish_reason', ['MAX_TOKENS', 'SAFETY', 'RECITATION', None])
def test_resposta_nao_concluida_nao_e_aceita_mesmo_com_json_valido(finish_reason, image_data, provider):
    response = provider_response(model_result())
    response.json.return_value['candidates'][0]['finishReason'] = finish_reason
    provider.return_value = response
    assert_manual_only(*vision.analisar_imagem_com_ia(image_data))


@pytest.mark.parametrize('confidence', ['baixa', 'media', '', None])
def test_ocr_nao_confirmado_nao_retorna_dados_pessoais(confidence, image_data, provider):
    provider.return_value = provider_response(model_result(
        ocr_confianca=confidence, ocr_texto='Aluno Nome Completo RM12345',
        ocr_nome_aluno='Nome Completo', ocr_rm='12345', ocr_serie='2A'))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is True
    for field in ['ocr_texto', 'ocr_nome_aluno', 'ocr_rm', 'ocr_serie']:
        assert result[field] == ''


def test_ocr_confirmado_e_preservado_apenas_com_objeto_identificado(image_data, provider):
    provider.return_value = provider_response(model_result(
        ocr_confianca='alta', ocr_nome_aluno='Nome Completo', ocr_rm='12345'))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['ocr_nome_aluno'] == 'Nome Completo'
    assert result['ocr_rm'] == '12345'
    provider.return_value = provider_response(model_result(
        confianca_objeto='baixa', ocr_confianca='alta',
        ocr_nome_aluno='Nome Completo', ocr_rm='12345'))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is False
    assert result['ocr_nome_aluno'] == result['ocr_rm'] == ''


@pytest.mark.parametrize(('category', 'expected'), [
    ('eletronicos', 'ELETRÔNICOS'),
    ('acessórios', 'ACESSÓRIOS'),
    ('mochila', 'MOCHILA'),
    ('roupas', 'ROUPAS'),
    ('escolares', 'ESCOLARES'),
    ('categoria inventada', 'OUTROS'),
])
def test_categorias_sao_convertidas_para_valores_do_formulario(category, expected, image_data, provider):
    provider.return_value = provider_response(model_result(categoria=category))
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['categoria'] == expected


def test_modelo_configuravel_e_chave_fora_da_url(image_data, provider, monkeypatch):
    monkeypatch.setenv('GEMINI_VISION_MODEL', 'modelo-de-teste-1.0')
    provider.return_value = provider_response(model_result())
    result, error = vision.analisar_imagem_com_ia(image_data)
    assert error is None
    assert result['pode_preencher'] is True
    assert provider.call_args.args[0] == (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        'modelo-de-teste-1.0:generateContent')
    assert provider.call_args.kwargs['headers']['x-goog-api-key'] == 'chave-ficticia-dos-testes'


def test_mime_e_determinado_pelos_bytes_e_nao_pelo_data_uri(image_data, provider):
    provider.return_value = provider_response(model_result())
    mislabeled_image = image_data.replace('image/png', 'image/jpeg')
    result, error = vision.analisar_imagem_com_ia(mislabeled_image)
    assert error is None
    assert result['pode_preencher'] is True
    payload = provider.call_args.kwargs['json']
    assert payload['contents'][0]['parts'][1]['inline_data']['mime_type'] == 'image/png'


def test_backend_de_producao_usa_o_servico_canonico():
    assert server.analisar_imagem_com_ia is vision.analisar_imagem_com_ia


def test_endpoint_nao_consulta_alunos_quando_identificacao_nao_e_confiavel(image_data, provider, monkeypatch):
    server.app.config['TESTING'] = True
    monkeypatch.setattr(server.limiter, 'enabled', False)
    # Mesmo que o provedor sugira OCR, a baixa confiança impede preenchimento
    # e cruzamento com um cadastro real.
    provider.return_value = provider_response(model_result(
        confianca_objeto='baixa', ocr_rm='12345', ocr_nome_aluno='Nome sugerido'))
    database = Mock(side_effect=AssertionError('A identificação não permite consultar alunos'))
    monkeypatch.setattr(server, 'get_db_connection', database)
    response = server.app.test_client().post('/api/ia/analisar-imagem', json={'foto': image_data})
    assert response.status_code == 200
    assert response.json['resultado']['pode_preencher'] is False
    assert response.json['resultado']['aluno_correspondente'] is None
    database.assert_not_called()
