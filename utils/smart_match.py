"""
Módulo de Heurística de Smart Matching com Similaridade Semântica (Fase 3)
Calcula pontuação percentual de afinidade entre relatos de perda e itens catalogados,
incorporando reconhecimento de categorias, termos exatos, sinônimos, cores e locais.
"""
import re
from utils.helpers import extrair_termos, expandir_termos_semanticos

CORES_LISTA = {
    'preto', 'preta', 'azul', 'vermelho', 'vermelha', 'rosa', 'verde', 
    'amarelo', 'amarela', 'cinza', 'branco', 'branca', 'prata', 'dourado', 
    'marrom', 'roxo', 'roxa', 'laranja', 'bege', 'vinho', 'grafite'
}

def calcular_smart_match(relato, item):
    """
    Heurística ponderada de correlação com IA Semântica:
    - 30 pts: Categoria exata
    - até 40 pts: Termos coincidentes na descrição/título + Sinônimos contextuais
    - 15 pts: Cores coincidentes
    - 15 pts: Local compatível mencionado no relato
    Retorna: (score_int [0-100], lista_de_motivos)
    """
    score = 0
    detalhes = []
    
    # 1. Categoria (30 pts)
    cat_relato = (relato.get('categoria') or '').strip().upper()
    cat_item = (item.get('categoria') or '').strip().upper()
    if cat_relato and cat_item and cat_relato == cat_item:
        score += 30
        detalhes.append(f"Mesma categoria ({cat_relato})")
    
    # 2. Termos do texto + Semântica (até 40 pts)
    txt_relato = (relato.get('descricao') or '')
    txt_item = f"{item.get('nome') or ''} {item.get('txt_descricao') or item.get('descricao') or ''}"
    termos_relato = extrair_termos(txt_relato)
    termos_item = extrair_termos(txt_item)
    
    intersecao_exata = termos_relato.intersection(termos_item)
    expandidos_relato = expandir_termos_semanticos(termos_relato)
    sinonimos_encontrados = expandidos_relato.intersection(termos_item) - intersecao_exata

    if termos_relato:
        valor_termos = len(intersecao_exata) * 1.0 + len(sinonimos_encontrados) * 0.75
        pct_termos = valor_termos / max(1, len(termos_relato))
        pts_termos = min(40, round(pct_termos * 40))
        score += pts_termos
        
        if intersecao_exata:
            detalhes.append(f"Termos coincidentes: {', '.join(sorted(list(intersecao_exata))[:3])}")
        if sinonimos_encontrados:
            detalhes.append(f"Sinônimo identificado por IA: {', '.join(sorted(list(sinonimos_encontrados))[:2])}")
    
    # 3. Cores (15 pts)
    palavras_relato = set(re.findall(r'[a-zA-Záéíóúãõâêîôûç]+', txt_relato.lower()))
    palavras_item = set(re.findall(r'[a-zA-Záéíóúãõâêîôûç]+', txt_item.lower()))
    cores_relato = palavras_relato.intersection(CORES_LISTA)
    cores_item = palavras_item.intersection(CORES_LISTA)
    cores_comuns = cores_relato.intersection(cores_item)
    if cores_comuns:
        score += 15
        detalhes.append(f"Cor compatível: {', '.join(sorted(list(cores_comuns)))}")
        
    # 4. Local (15 pts)
    local_item = (item.get('txt_local') or item.get('local_encontrado') or '').lower().strip()
    if local_item and len(local_item) > 2 and local_item in txt_relato.lower():
        score += 15
        detalhes.append(f"Local compatível ({local_item})")
        
    return min(100, score), detalhes
