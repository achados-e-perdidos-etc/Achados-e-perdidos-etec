# tests/test_features.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_fast_drop_bloqueado_no_pc(client):
    """Garante que o acesso ao Fast Drop via PC (User-Agent Desktop) seja bloqueado."""
    response = client.post('/api/fast-drop', 
                            json={'foto_base64': 'data:image/png;base64,...'},
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert response.status_code == 403
    data = response.get_json()
    assert "exclusivo para dispositivos móveis" in data['erro']

def test_fast_drop_permitido_mobile(client):
    """Garante que o Fast Drop funcione em dispositivos móveis (Mobile PWA)."""
    response = client.post('/api/fast-drop', 
                            json={'foto_base64': 'data:image/png;base64,...', 'is_mobile_test': True},
                            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['sucesso'] is True

def test_sanitizacao():
    from extensions import sanitizar_input
    perigoso = "<script>alert('xss')</script>Teste"
    seguro = sanitizar_input(perigoso)
    assert "<script>" not in seguro
    assert "&lt;script&gt;" in seguro
