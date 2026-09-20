"""
Serviço de Inteligência Artificial e Visão Computacional (Fase 3)
Auto-tagging multimodal e extração de atributos visuais de fotos de pertences.
Suporta Google Gemini Vision API e fallback local resiliente com Pillow.
"""
import os
import io
import re
import json
import base64
import requests
from PIL import Image

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "").strip()

# Mapeamento de cores RGB para nomes em português (para o detector local de visão)
CORES_RGB = [
    ("preto", (20, 20, 20)),
    ("branco", (235, 235, 235)),
    ("cinza", (128, 128, 128)),
    ("azul", (30, 80, 190)),
    ("vermelho", (200, 30, 30)),
    ("verde", (35, 145, 55)),
    ("amarelo", (230, 210, 30)),
    ("rosa", (230, 100, 150)),
    ("roxo", (120, 40, 160)),
    ("marrom", (110, 60, 30)),
    ("laranja", (230, 110, 20))
]

def _distancia_cor(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5

def extrair_cores_predominantes_local(imagem_bytes):
    """
    Fallback de visão computacional local utilizando Pillow:
    Analisa os pixels da imagem e identifica até 2 tonalidades dominantes.
    """
    try:
        img = Image.open(io.BytesIO(imagem_bytes)).convert('RGB')
        img.thumbnail((60, 60))
        pixels = list(img.getdata())
        
        contagem = {}
        for r, g, b in pixels:
            # Encontra a cor mais próxima
            cor_mais_proxima = min(CORES_RGB, key=lambda item: _distancia_cor((r, g, b), item[1]))[0]
            contagem[cor_mais_proxima] = contagem.get(cor_mais_proxima, 0) + 1
            
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        return [cor for cor, _ in ranking[:2]]
    except Exception as e:
        print(f"[Visão Local] Erro ao extrair cores: {e}")
        return ["cinza"]

def analisar_imagem_com_ia(imagem_entrada):
    """
    Processa a imagem (Base64 ou URL) e extrai:
    - Título sugerido
    - Categoria adequada para o sistema da ETEC
    - Cores predominantes
    - Descrição detalhada do estado e particularidades
    - Tags para facilitar busca
    """
    if not imagem_entrada:
        return None, "Imagem não fornecida."

    img_b64 = ""
    img_bytes = None
    mime_type = "image/jpeg"

    # Tratamento de entrada (URL ou Base64)
    if str(imagem_entrada).startswith('http'):
        try:
            res = requests.get(imagem_entrada, timeout=8)
            img_bytes = res.content
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            if 'png' in imagem_entrada.lower():
                mime_type = "image/png"
        except Exception as e:
            return None, f"Falha ao baixar imagem remota: {e}"
    elif "base64," in str(imagem_entrada):
        partes = str(imagem_entrada).split("base64,")
        img_b64 = partes[1]
        img_bytes = base64.b64decode(img_b64)
        if "image/png" in partes[0]:
            mime_type = "image/png"
    else:
        img_b64 = str(imagem_entrada)
        try:
            img_bytes = base64.b64decode(img_b64)
        except Exception:
            pass

    # 1. Tentativa via Google Gemini Multimodal se chave disponível
    if GEMINI_API_KEY and img_b64:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = """
Você é o assistente de inteligência artificial do sistema de Achados e Perdidos da ETEC (Centro Paula Souza).
Analise com atenção a fotografia deste pertence encontrado na escola.
Gere estritamente um JSON VÁLIDO (sem qualquer bloco de código ```json``` ou texto explicativo), no formato:
{
  "nome": "Título conciso em português (ex: Garrafa Térmica Azul 500ml)",
  "categoria": "Escolha UMA entre: MOCHILA, ROUPAS, ACESSÓRIOS, ESCOLARES, ELETRÔNICOS, OUTROS",
  "cores": ["cor1", "cor2"],
  "descricao": "Descrição visual objetiva (marcas aparentes, estampas, zíperes, avarias ou adesivos)",
  "tags": ["palavra1", "palavra2", "palavra3"]
}
"""
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": img_b64
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 600
                }
            }
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Remove possíveis marcadores markdown
                raw_text = re.sub(r'^```json\s*', '', raw_text)
                raw_text = re.sub(r'\s*```$', '', raw_text).strip()
                resultado = json.loads(raw_text)
                resultado['metodo'] = 'gemini_vision'
                return resultado, None
        except Exception as e:
            print(f"[Gemini Vision API] Fallback para visão local devido a: {e}")

    # 2. Fallback resiliente com análise local (Pillow + Heurística)
    cores_detectadas = []
    if img_bytes:
        cores_detectadas = extrair_cores_predominantes_local(img_bytes)
        
    cores_str = ', '.join(cores_detectadas) if cores_detectadas else 'não identificada'
    resultado_fallback = {
        "nome": f"Item Escolar ({cores_str.title()})",
        "categoria": "OUTROS",
        "cores": cores_detectadas,
        "descricao": f"Pertence com tonalidade {cores_str} registrado via análise visual.",
        "tags": cores_detectadas + ["etec", "achados"],
        "metodo": "visao_local_fallback"
    }
    return resultado_fallback, None
