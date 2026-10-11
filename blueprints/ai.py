from flask import Blueprint, request, jsonify
import logging
from services.ai_vision_service import analisar_imagem_com_ia
from utils.helpers import calcular_afinidade_semantica

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ia/analisar-imagem', methods=['OPTIONS', 'POST'])
def rota_analisar_imagem():
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
