import os, io, re, json, base64, requests
import unicodedata
from PIL import Image

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "")).strip()

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
        pixels = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
        contagem = {}
        for r, g, b in pixels:
            cor = min(CORES_RGB, key=lambda item: _distancia_cor((r, g, b), item[1]))[0]
            contagem[cor] = contagem.get(cor, 0) + 1
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranking[:2]]
    except Exception:
        return []

MAX_IMAGE_BYTES = 8 * 1024 * 1024
PROMPT = 'Você é um sistema de visão computacional especializado em identificar objetos perdidos em uma escola brasileira. Examine a imagem com atenção e retorne SOMENTE um objeto JSON válido, sem Markdown.\n\nPRIORIDADE MÁXIMA — IDENTIFICAÇÃO DO OBJETO:\n1. Diga o nome específico do objeto visível, não uma descrição genérica. Exemplos: "Caderno espiral", "Cubo mágico 3x3", "Lápis grafite", "Caneta azul", "Estojo escolar", "Mochila", "Garrafa de água", "Carteirinha de estudante", "Livro didático", "Fone de ouvido", "Chaveiro".\n2. Diferencie objetos parecidos: caderno vs. livro; lápis vs. caneta; cubo mágico (peça cúbica com quadradinhos coloridos) vs. dado; estojo vs. carteira; garrafa vs. copo. Use detalhes visuais observáveis para decidir.\n3. Se houver vários objetos, escolha como principal o item que está mais centralizado, maior ou claramente destacado. Mencione os demais brevemente na descrição, sem misturar os nomes.\n4. Não deduza marca, material, conteúdo ou função que não esteja visível. Não invente características. Se não der para distinguir, não adivinhe: deixe nome e descrição vazios, use confiança baixa e explique a incerteza.\n5. O título deve ser curto e específico, de preferência 2 a 6 palavras. Nunca use títulos vagos como "Item Escolar", "Objeto" ou somente a cor quando o objeto for reconhecível.\n6. A descrição deve ter 1 a 3 frases úteis para diferenciar o item: formato, padrão, tipo de fechamento, estampa, número de peças, texto ou marcas visíveis. Inclua as cores relevantes sem substituir o nome do objeto.\n7. Escolha categoria compatível com a lista de categorias existentes: "ESCOLARES", "MOCHILA", "ELETRÔNICOS", "ROUPAS", "ACESSÓRIOS" ou "OUTROS". Use "ESCOLARES" para caderno, lápis, caneta, cubo mágico, livro, estojo e material de estudo; "MOCHILA" para mochilas; "ELETRÔNICOS" para fones e aparelhos; "ACESSÓRIOS" para chaveiros e objetos pessoais semelhantes. Se a escola usar outro nome de categoria, escolha a opção mais próxima.\n8. Liste até 3 cores visivelmente presentes. Não confunda o fundo da foto com a cor do objeto.\n\nOCR / DADOS PESSOAIS:\nLeia apenas texto realmente legível em carteirinhas, cadernos, agendas ou etiquetas. Nunca invente nomes, RM, série ou números. RM só deve ser preenchido quando houver evidência de matrícula/registro acadêmico. Caso contrário, use string vazia.\n\nRetorne exatamente estes campos:\n{"nome":"nome específico do objeto","categoria":"ESCOLARES","cores":["azul","preto"],"descricao":"descrição visual específica e objetiva","tags":["caderno","espiral"],"confianca_objeto":"alta|media|baixa","alternativas":["nome alternativo se houver dúvida"],"objetos_detectados":["objeto principal","outro objeto visível"],"ocr_texto":"texto realmente legível","ocr_nome_aluno":"","ocr_rm":"","ocr_serie":"","tipo_documento":"","ocr_confianca":"baixa|media|alta"}\n\nA confiança deve refletir a imagem: alta se o tipo de objeto estiver claro; média se houver alguma dúvida; baixa se estiver desfocado, pequeno ou parcialmente oculto. "alternativas" pode ser uma lista vazia. Não retorne comentários fora do JSON.'


def _texto(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ''


def _lista(value, limit, length):
    return [_texto(item, length) for item in value[:limit] if _texto(item, length)] if isinstance(value, list) else []


def _manual(img_bytes, motivo):
    return {
        'nome': '', 'descricao': '', 'categoria': 'OUTROS',
        'cores': extrair_cores_predominantes_local(img_bytes), 'tags': [],
        'metodo': 'visao_local_fallback', 'confianca_objeto': 'baixa',
        'pode_preencher': False, 'alternativas': [], 'objetos_detectados': [],
        'ocr_texto': '', 'ocr_nome_aluno': '', 'ocr_rm': '', 'ocr_serie': '',
        'tipo_documento': '', 'ocr_confianca': 'baixa', 'aviso': motivo
    }, None


def analisar_imagem_com_ia(imagem_entrada):
    if not isinstance(imagem_entrada, str) or not imagem_entrada.strip():
        return None, 'Imagem não fornecida.'
    try:
        if imagem_entrada.startswith(('https://', 'http://')):
            # A bounded stream avoids loading unbounded downloads into memory.
            from urllib.parse import urlsplit
            from config import CLOUDINARY_CLOUD_NAME
            endereco=urlsplit(imagem_entrada)
            if (endereco.scheme!='https' or endereco.hostname!='res.cloudinary.com' or endereco.username or endereco.password
                or not CLOUDINARY_CLOUD_NAME or not endereco.path.startswith('/'+CLOUDINARY_CLOUD_NAME+'/image/upload/')):
                return None, 'Selecione o arquivo da foto; links externos não são aceitos.'
            with requests.get(imagem_entrada, timeout=8, allow_redirects=False, stream=True) as res:
                if res.status_code != 200:
                    return None, 'Não foi possível obter a imagem.'
                chunks, size = [], 0
                for chunk in res.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        return None, 'Imagem excede 8 MB.'
                    chunks.append(chunk)
                img_bytes = b''.join(chunks)
        else:
            encoded = imagem_entrada.split('base64,', 1)[-1].strip()
            if len(encoded) > 11_500_000:
                return None, 'Imagem excede 8 MB.'
            img_bytes = base64.b64decode(encoded, validate=True)
        if not img_bytes or len(img_bytes) > MAX_IMAGE_BYTES:
            return None, 'Imagem inválida ou maior que 8 MB.'
        with Image.open(io.BytesIO(img_bytes)) as image:
            if image.width * image.height > 16_000_000:
                return None, 'A resolução da imagem excede o limite de 16 megapixels.'
            mime_type = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}.get(image.format)
            if not mime_type:
                return None, 'Use uma imagem PNG, JPEG ou WEBP.'
            image.verify()
    except Exception:
        return None, 'Não foi possível ler a imagem. Selecione uma foto válida.'

    if not GEMINI_API_KEY:
        return _manual(img_bytes, 'Identificação visual indisponível. Preencha manualmente; estimar cores não identifica o objeto.')
    model = os.environ.get('GEMINI_VISION_MODEL', 'gemini-2.5-flash').strip()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}', model):
        return _manual(img_bytes, 'O modelo de análise não está configurado corretamente. Preencha manualmente.')
    try:
        resp = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': GEMINI_API_KEY},
            json={'contents': [{'parts': [{'text': PROMPT}, {'inline_data': {
                'mime_type': mime_type, 'data': base64.b64encode(img_bytes).decode('ascii')}}]}],
                'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 1600,
                                     'responseMimeType': 'application/json'}}, timeout=20)
        if resp.status_code != 200:
            return _manual(img_bytes, 'O serviço de identificação está indisponível. Seus campos foram preservados; preencha manualmente ou tente novamente.')
        candidate = resp.json()['candidates'][0]
        if candidate.get('finishReason') != 'STOP':
            return _manual(img_bytes, 'A análise não foi concluída. Preencha manualmente ou tente novamente.')
        raw = ''.join(part.get('text', '') for part in candidate['content']['parts'] if not part.get('thought'))
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw).strip()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError('Resposta sem objeto JSON')
        result = {key: _texto(value.get(key), limit) for key, limit in
                  [('nome', 120), ('descricao', 1200), ('ocr_texto', 1000),
                   ('ocr_nome_aluno', 100), ('ocr_rm', 20), ('ocr_serie', 50), ('tipo_documento', 80)]}
        confidence = _texto(value.get('confianca_objeto'), 10).lower()
        result['confianca_objeto'] = confidence if confidence in ('alta', 'media', 'baixa') else 'baixa'
        allowed = ['ESCOLARES', 'MOCHILA', 'ELETRÔNICOS', 'ROUPAS', 'ACESSÓRIOS', 'OUTROS']
        normalize = lambda text: ''.join(c for c in unicodedata.normalize('NFD', text.upper()) if not unicodedata.combining(c))
        category = _texto(value.get('categoria'), 50)
        result['categoria'] = next((c for c in allowed if normalize(c) == normalize(category)), 'OUTROS')
        for key, count, length in [('cores',3,30), ('tags',8,40), ('alternativas',3,80), ('objetos_detectados',5,80)]:
            result[key] = _lista(value.get(key), count, length)
        result['metodo'] = 'gemini_vision_ocr'
        result['pode_preencher'] = bool(result['nome'] and result['descricao']
            and result['confianca_objeto'] in ('alta', 'media')
            and result['nome'].lower() not in ('item', 'objeto', 'item escolar', 'objeto escolar'))
        result['ocr_confianca'] = 'alta' if value.get('ocr_confianca') == 'alta' else 'baixa'
        result['ocr_revisar'] = [] if result['ocr_confianca']=='alta' else ['nome','rm']
        if not result['pode_preencher'] or result['ocr_confianca'] != 'alta':
            for key in ('ocr_texto', 'ocr_nome_aluno', 'ocr_rm', 'ocr_serie'):
                result[key] = ''
        result['aviso'] = 'Confira as sugestões antes de salvar.' if result['pode_preencher'] else 'A imagem não permitiu identificar o objeto com segurança. Seus campos foram preservados; preencha manualmente.'
        return result, None
    except Exception:
        # Do not log provider URLs, keys or OCR of personal documents.
        return _manual(img_bytes, 'A análise não retornou uma identificação utilizável. Preencha manualmente ou tente novamente.')
