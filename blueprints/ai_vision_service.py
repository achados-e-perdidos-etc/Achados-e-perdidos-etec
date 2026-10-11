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
            res = requests.get(imagem_entrada, timeout=8, allow_redirects=False)
            res.raise_for_status()
            if len(res.content) > 8 * 1024 * 1024: return None, "Imagem excede 8 MB."
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
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_VISION_MODEL', 'gemini-2.5-flash')}:generateContent?key={GEMINI_API_KEY}"
            prompt = """Você é um sistema de visão computacional especializado em identificar objetos perdidos em uma escola brasileira. Examine a imagem com atenção e retorne SOMENTE um objeto JSON válido, sem Markdown.

PRIORIDADE MÁXIMA — IDENTIFICAÇÃO DO OBJETO:
1. Diga o nome específico do objeto visível, não uma descrição genérica. Exemplos: "Caderno espiral", "Cubo mágico 3x3", "Lápis grafite", "Caneta azul", "Estojo escolar", "Mochila", "Garrafa de água", "Carteirinha de estudante", "Livro didático", "Fone de ouvido", "Chaveiro".
2. Diferencie objetos parecidos: caderno vs. livro; lápis vs. caneta; cubo mágico (peça cúbica com quadradinhos coloridos) vs. dado; estojo vs. carteira; garrafa vs. copo. Use detalhes visuais observáveis para decidir.
3. Se houver vários objetos, escolha como principal o item que está mais centralizado, maior ou claramente destacado. Mencione os demais brevemente na descrição, sem misturar os nomes.
4. Não deduza marca, material, conteúdo ou função que não esteja visível. Não invente características. Se não der para distinguir, use o nome mais provável com confiança baixa e explique a incerteza.
5. O título deve ser curto e específico, de preferência 2 a 6 palavras. Nunca use títulos vagos como "Item Escolar", "Objeto" ou somente a cor quando o objeto for reconhecível.
6. A descrição deve ter 1 a 3 frases úteis para diferenciar o item: formato, padrão, tipo de fechamento, estampa, número de peças, texto ou marcas visíveis. Inclua as cores relevantes sem substituir o nome do objeto.
7. Escolha categoria compatível com a lista de categorias existentes: "ESCOLARES", "MOCHILA", "ELETRÔNICOS", "ROUPAS", "ACESSÓRIOS" ou "OUTROS". Use "ESCOLARES" para caderno, lápis, caneta, cubo mágico, livro, estojo e material de estudo; "MOCHILA" para mochilas; "ELETRÔNICOS" para fones e aparelhos; "ACESSÓRIOS" para chaveiros e objetos pessoais semelhantes. Se a escola usar outro nome de categoria, escolha a opção mais próxima.
8. Liste até 3 cores visivelmente presentes. Não confunda o fundo da foto com a cor do objeto.

OCR / DADOS PESSOAIS:
Leia apenas texto realmente legível em carteirinhas, cadernos, agendas ou etiquetas. Nunca invente nomes, RM, série ou números. RM só deve ser preenchido quando houver evidência de matrícula/registro acadêmico. Caso contrário, use string vazia.

Retorne exatamente estes campos:
{"nome":"nome específico do objeto","categoria":"ESCOLARES","cores":["azul","preto"],"descricao":"descrição visual específica e objetiva","tags":["caderno","espiral"],"confianca_objeto":"alta|media|baixa","alternativas":["nome alternativo se houver dúvida"],"objetos_detectados":["objeto principal","outro objeto visível"],"ocr_texto":"texto realmente legível","ocr_nome_aluno":"","ocr_rm":"","ocr_serie":"","tipo_documento":"","ocr_confianca":"baixa|media|alta"}

A confiança deve refletir a imagem: alta se o tipo de objeto estiver claro; média se houver alguma dúvida; baixa se estiver desfocado, pequeno ou parcialmente oculto. "alternativas" pode ser uma lista vazia. Não retorne comentários fora do JSON."""
            payload = {
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": img_b64}}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1200, "responseMimeType": "application/json"}
            }
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                raw_text = re.sub(r'^```json\s*', '', raw_text)
                raw_text = re.sub(r'\s*```$', '', raw_text).strip()
                resultado = json.loads(raw_text)
                resultado['metodo'] = 'gemini_vision_ocr'
                for key in ('ocr_texto', 'ocr_nome_aluno', 'ocr_rm', 'ocr_serie', 'tipo_documento', 'ocr_confianca'):
                    resultado[key] = str(resultado.get(key) or '').strip()[:1000]
                resultado['cores'] = [str(c).strip()[:30] for c in resultado.get('cores', [])[:3] if str(c).strip()] if isinstance(resultado.get('cores'), list) else []
                resultado['tags'] = [str(t).strip()[:40] for t in resultado.get('tags', [])[:8] if str(t).strip()] if isinstance(resultado.get('tags'), list) else []
                resultado['alternativas'] = [str(t).strip()[:80] for t in resultado.get('alternativas', [])[:3] if str(t).strip()] if isinstance(resultado.get('alternativas'), list) else []
                resultado['objetos_detectados'] = [str(t).strip()[:80] for t in resultado.get('objetos_detectados', [])[:5] if str(t).strip()] if isinstance(resultado.get('objetos_detectados'), list) else []
                resultado['confianca_objeto'] = str(resultado.get('confianca_objeto') or 'media').lower()[:10]
                if resultado['confianca_objeto'] not in ('alta', 'media', 'baixa'): resultado['confianca_objeto'] = 'media'
                resultado['nome'] = str(resultado.get('nome') or 'Objeto não identificado').strip()[:120]
                resultado['descricao'] = str(resultado.get('descricao') or 'Objeto escolar; confira visualmente a foto.').strip()[:1200]
                return resultado, None
        except Exception as e:
            print(f"[Gemini] Falha: {e}")

    cores = extrair_cores_predominantes_local(img_bytes) if img_bytes else []
    cores_str = ', '.join(cores) if cores else 'não identificada'
    resultado_fallback = {
        "nome": "Objeto não identificado automaticamente",
        "categoria": "OUTROS",
        "cores": cores,
        "descricao": f"A IA visual não está disponível; apenas as cores aproximadas foram estimadas ({cores_str}). Confira a foto e informe o tipo de objeto manualmente.",
        "tags": cores + ["etec", "achados"],
        "confianca_objeto": "baixa", "alternativas": [], "objetos_detectados": [],
        "metodo": "visao_local_fallback", "aviso": "Configure GEMINI_API_KEY para habilitar a identificação visual por IA."
    }
    return resultado_fallback, None
