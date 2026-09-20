"""
Blueprint de Inteligência Artificial e Visão Computacional (Fase 3)
Rotas de auto-tagging de imagens e processamento de linguagem natural (NLP).
"""
from flask import Blueprint, request, jsonify
from services.ai_vision_service import analisar_imagem_com_ia
from utils.helpers import calcular_afinidade_semantica

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ia/analisar-imagem', methods=['OPTIONS', 'POST'])
def rota_analisar_imagem():
    """
    Recebe a imagem de um item (Base64 ou URL) e retorna sugestões
    de nome, categoria, cores, descrição detalhada e tags geradas por IA.
    """
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    dados = request.json or {}
    foto = dados.get('foto') or dados.get('imagem')
    
    if not foto:
        return jsonify({"success": False, "message": "Nenhuma imagem informada para análise."}), 400

    resultado, erro = analisar_imagem_com_ia(foto)
    if erro:
        return jsonify({"success": False, "message": erro}), 500

    return jsonify({
        "success": True,
        "resultado": resultado
    })

@ai_bp.route('/api/ia/comparar-semantica', methods=['OPTIONS', 'POST'])
def rota_comparar_semantica():
    """
    Compara duas descrições de texto e avalia a afinidade semântica
    utilizando a expansão léxica de sinônimos escolares.
    """
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    dados = request.json or {}
    texto_a = dados.get('texto_a') or dados.get('relato') or ''
    texto_b = dados.get('texto_b') or dados.get('item') or ''

    score, motivos = calcular_afinidade_semantica(texto_a, texto_b)
    
    return jsonify({
        "success": True,
        "score_percentual": round(score * 100, 1),
        "motivos": motivos
    })
