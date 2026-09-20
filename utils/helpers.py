"""
Funções Utilitárias Gerais
Processamento de texto, validação de regras de negócio e cálculo de datas.
"""
import re
from datetime import datetime
from config import DOMINIOS_EMAIL_PERMITIDOS

STOPWORDS = {
    'perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do',
    'com', 'sem', 'favor', 'acho', 'que', 'para', 'pela', 'pelo', 'onde',
    'qual', 'quem', 'isso', 'esse', 'essa', 'este', 'esta', 'seja', 'ser'
}

def extrair_termos(texto):
    """
    Extrai palavras-chave significativas ignorando stopwords e caracteres especiais.
    """
    if not texto:
        return set()
    palavras = re.findall(r'[a-zA-Z0-9áéíóúãõâêîôûç]+', str(texto).lower())
    termos = set()
    for p in palavras:
        if len(p) >= 3 and p not in STOPWORDS:
            termos.add(p)
    return termos

def calcular_dias_passados(data_str):
    """
    Calcula o número de dias corridos entre a data informada e o momento atual.
    Suporta múltiplos formatos de data brasileiros e ISO.
    """
    if not data_str:
        return 0
    data_limpa = str(data_str).strip()
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']
    for fmt in formatos:
        try:
            dt = datetime.strptime(data_limpa, fmt)
            return max(0, (datetime.now() - dt).days)
        except Exception:
            continue
    return 0

def validar_email_institucional(email):
    """
    Valida se o endereço de e-mail pertence aos domínios oficiais do CPS/ETEC.
    Exemplo: nome.sobrenome@aluno.cps.sp.gov.br
    """
    if not email or not isinstance(email, str):
        return False, "E-mail não informado."
    email_limpo = email.strip().lower()
    
    # Validação de formato básico de e-mail (RFC simplificado)
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(padrao, email_limpo):
        return False, "Formato de e-mail inválido."
        
    valido = any(email_limpo.endswith(dom) for dom in DOMINIOS_EMAIL_PERMITIDOS)
    if not valido:
        return False, f"Apenas e-mails institucionais ({', '.join(DOMINIOS_EMAIL_PERMITIDOS)}) são permitidos."
    return True, email_limpo

def sanitizar_texto(texto, max_len=500):
    """
    Sanitiza strings de entrada para evitar injeções ou poluição visual.
    """
    if not texto:
        return ""
    texto_str = str(texto).strip()
    # Remove caracteres de controle estranhos mantendo acentuação e pontuação comum
    texto_limpo = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto_str)
    return texto_limpo[:max_len]


# ==============================================================================
# FASE 3: GRUPOS SEMÂNTICOS E EXPANSÃO LÉXICA DE SINÔNIMOS ESCOLARES
# ==============================================================================

GRUPOS_SINONIMOS = [
    # Agasalhos e Roupas
    {'moletom', 'casaco', 'blusa', 'jaqueta', 'agasalho', 'sueter', 'corta-vento', 'cardigan'},
    {'calça', 'bermuda', 'shorts', 'legging', 'jeans'},
    {'camiseta', 'camisa', 'regata', 'uniforme'},
    {'tenis', 'calcado', 'sapato', 'sandalia', 'chinelo'},
    
    # Material Escolar
    {'estojo', 'penal', 'necessaire'},
    {'caderno', 'bloco', 'agenda', 'fichario', 'planner'},
    {'livro', 'apostila', 'manual', 'dicionario'},
    {'caneta', 'lapiseira', 'lapis', 'marcador', 'marca-texto'},
    
    # Recipientes e Acessórios
    {'garrafa', 'squeeze', 'termica', 'cantil', 'garrafinha', 'copo'},
    {'mochila', 'bolsa', 'sacola', 'mala', 'pochete', 'bag'},
    {'oculos', 'armacao', 'lente'},
    {'chave', 'chaveiro', 'cadeado', 'tag'},
    {'guarda-chuva', 'sombrinha'},
    {'bone', 'chapeu', 'touca', 'gorro'},
    
    # Eletrônicos
    {'fone', 'headphone', 'headset', 'airpods', 'earbuds', 'auricular'},
    {'carregador', 'cabo', 'adaptador', 'fonte', 'usb'},
    {'celular', 'smartphone', 'telefone', 'iphone', 'motorola', 'samsung', 'xiaomi'},
    {'calculadora', 'cientifica'}
]

def expandir_termos_semanticos(termos_set):
    termos_expandidos = set(termos_set)
    for termo in termos_set:
        termo_limpo = termo.lower().strip()
        for grupo in GRUPOS_SINONIMOS:
            if termo_limpo in grupo:
                termos_expandidos.update(grupo)
    return termos_expandidos

def calcular_afinidade_semantica(texto_a, texto_b):
    termos_a = extrair_termos(texto_a)
    termos_b = extrair_termos(texto_b)
    
    if not termos_a or not termos_b:
        return 0.0, []
        
    intersecao_exata = termos_a.intersection(termos_b)
    expandidos_a = expandir_termos_semanticos(termos_a)
    expandidos_b = expandir_termos_semanticos(termos_b)
    
    intersecao_semantica = expandidos_a.intersection(termos_b).union(expandidos_b.intersection(termos_a))
    sinonimos_encontrados = list(intersecao_semantica - intersecao_exata)
    
    denominador = max(len(termos_a), len(termos_b))
    score = (len(intersecao_exata) * 1.0 + len(sinonimos_encontrados) * 0.75) / max(1, denominador)
    score_normalizado = min(1.0, score)
    
    motivos = []
    if intersecao_exata:
        motivos.append(f"Termos idênticos: {', '.join(sorted(list(intersecao_exata))[:3])}")
    if sinonimos_encontrados:
        motivos.append(f"Sinônimos equivalentes detectados: {', '.join(sorted(sinonimos_encontrados)[:3])}")
        
    return score_normalizado, motivos
