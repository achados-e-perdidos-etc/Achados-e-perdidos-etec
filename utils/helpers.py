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
