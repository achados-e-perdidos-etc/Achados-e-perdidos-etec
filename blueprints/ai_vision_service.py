import os, io, re, json, base64, requests
from PIL import Image

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "").strip()

CORES_RGB = [
    ("preto", (20, 20, 20)), ("branco", (235, 235, 235)), ("cinza", (128, 128, 128)),
    ("azul", (30, 80, 190)), ("vermelho", (200, 30, 30)), ("verde", (35, 145, 55)),
    ("amarelo", (230, 210, 30)), ("rosa", (230, 100, 150)), ("roxo", (120, 40, 160)),
    ("marrom", (110, 60, 30)), ("laranja", (230, 110, 20))
]

def _distancia_cor(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5

def extrair_cores_predominantes_local(imagem_bytes):
    try:
        img = Image.open(io.BytesIO(imagem_bytes)).convert('RGB')
        img.thumbnail((60, 60))
        pixels = list(img.getdata())
        contagem = {}
        for r, g, b in pixels:
            cor = min(CORES_RGB, key=lambda item: _distancia_cor((r, g, b), item[1]))[0]
            contagem[cor] = contagem.get(cor, 0) + 1
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranking[:2]]
    except Exception:
        return ["cinza"]

def analisar_imagem_com_ia(imagem_entrada):
    if not imagem_entrada: return None, "Imagem não fornecida."
    img_b64 = ""
    img_bytes = None
    mime_type = "image/jpeg"

    if str(imagem_entrada).startswith('http'):
        try:
            res = requests.get(imagem_entrada, timeout=8)
            img_bytes = res.content
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            if 'png' in imagem_entrada.lower(): mime_type = "image/png"
        except Exception as e:
            return None, f"Falha ao baixar imagem: {e}"
    elif "base64," in str(imagem_entrada):
        partes = str(imagem_entrada).split("base64,")
        img_b64 = partes[1]
        try: img_bytes = base64.b64decode(img_b64)
        except Exception: pass
        if "image/png" in partes[0]: mime_type = "image/png"
    else:
        img_b64 = str(imagem_entrada)
        try: img_bytes = base64.b64decode(img_b64)
        except Exception: pass

    if GEMINI_API_KEY and img_b64:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = """Analise a foto do pertence escolar e retorne estritamente um JSON valido:
{"nome": "Titulo conciso", "categoria": "ROUPAS, ACESSORIOS, ESCOLARES, ELETRONICOS, MOCHILA ou OUTROS", "cores": ["cor1"], "descricao": "Descricao visual detalhada", "tags": ["tag1"]}"""
            payload = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": img_b64}}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500}
            }
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                raw_text = re.sub(r'^```json\s*', '', raw_text)
                raw_text = re.sub(r'\s*```$', '', raw_text).strip()
                resultado = json.loads(raw_text)
                resultado['metodo'] = 'gemini_vision'
                return resultado, None
        except Exception as e:
            print(f"[Gemini] Falha: {e}")

    cores = extrair_cores_predominantes_local(img_bytes) if img_bytes else []
    cores_str = ', '.join(cores) if cores else 'não identificada'
    resultado_fallback = {
        "nome": f"Item Escolar ({cores_str.title()})",
        "categoria": "OUTROS",
        "cores": cores,
        "descricao": f"Pertence com tonalidade {cores_str} analisado por visao local.",
        "tags": cores + ["etec", "achados"],
        "metodo": "visao_local_fallback"
    }
    return resultado_fallback, None
