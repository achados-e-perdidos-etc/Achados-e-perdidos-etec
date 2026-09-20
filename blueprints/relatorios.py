"""
Blueprint de Inteligência, Estatísticas (BI) e Smart Matching
Agrupamentos analíticos para gráficos, relatórios formais e cruzamento de dados.
"""
import json
from flask import Blueprint, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection, verificar_e_atualizar_itens_doacao
from utils.security import token_required
from utils.smart_match import calcular_smart_match

relatorios_bp = Blueprint('relatorios', __name__)

@relatorios_bp.route('/api/entregues', methods=['OPTIONS', 'GET'])
@token_required
def get_entregues():
    """Retorna o histórico de comprovantes e pertences devolvidos."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM entregues ORDER BY id DESC;")
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(res)

@relatorios_bp.route('/api/estatisticas', methods=['OPTIONS', 'GET'])
@token_required
def estatisticas():
    """
    Retorna métricas consolidadas de BI para os gráficos do Chart.js:
    - Total de itens cadastrados, entregues, para doação, disponíveis e solicitados.
    - Taxa de devolução percentual.
    - Agrupamento por categoria e por local encontrado na escola.
    """
    verificar_e_atualizar_itens_doacao()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE aprovado = TRUE;")
        total_cadastrados = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM entregues;")
        total_entregues = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE (status LIKE 'DOAÇÃO%' OR status LIKE 'DOACAO%') AND aprovado = TRUE;")
        total_doacoes = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE status = 'DISPONÍVEL' AND aprovado = TRUE;")
        total_disponiveis = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE status = 'SOLICITADO' AND aprovado = TRUE;")
        total_solicitados = cursor.fetchone()['total']

        # Agregação por categoria (gráfico de rosca)
        cursor.execute("""
            SELECT COALESCE(categoria, 'OUTROS') as categoria, COUNT(*) as qtd
            FROM itens
            WHERE aprovado = TRUE
            GROUP BY categoria
            ORDER BY qtd DESC;
        """)
        categorias = cursor.fetchall()
        
        # Agregação por local (gráfico de barras)
        cursor.execute("""
            SELECT COALESCE(local_encontrado, 'Indefinido') as local, COUNT(*) as qtd
            FROM itens
            WHERE aprovado = TRUE AND local_encontrado IS NOT NULL AND local_encontrado != '' AND local_encontrado != 'Indefinido'
            GROUP BY local_encontrado
            ORDER BY qtd DESC
            LIMIT 6;
        """)
        locais = cursor.fetchall()
        
        total_movimentado = total_cadastrados + total_entregues
        taxa_devolucao = round((total_entregues / total_movimentado * 100), 1) if total_movimentado > 0 else 0.0

        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "total_itens": total_cadastrados,
            "total_entregues": total_entregues,
            "total_doacoes": total_doacoes,
            "total_disponiveis": total_disponiveis,
            "total_solicitados": total_solicitados,
            "taxa_devolucao": taxa_devolucao,
            "por_categoria": categorias,
            "por_local": locais
        })
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@relatorios_bp.route('/api/smart-match', methods=['OPTIONS', 'GET'])
@token_required
def smart_match_api():
    """
    Motor analítico do Smart Match:
    Cruza todos os relatos abertos de perda com itens disponíveis no catálogo.
    Filtra correspondências com afinidade >= 45%.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro 
            FROM mural_perdidos 
            WHERE status = 'PROCURANDO' OR status IS NULL 
            ORDER BY id DESC;
        """)
        relatos = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, COALESCE(nome_item, descricao) as nome, descricao as txt_descricao, categoria, 
                   data_encontrado as txt_data, local_encontrado as txt_local, foto, fotos_json, status
            FROM itens 
            WHERE aprovado = TRUE AND status = 'DISPONÍVEL';
        """)
        itens = cursor.fetchall()
        for item in itens:
            try:
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except Exception:
                item['fotos'] = [item['foto']] if item.get('foto') else []

        resultados = []
        for r in relatos:
            matches_deste_relato = []
            for item in itens:
                score, motivos = calcular_smart_match(r, item)
                if score >= 45:
                    matches_deste_relato.append({
                        "item": item,
                        "score": score,
                        "motivos": motivos
                    })
            matches_deste_relato.sort(key=lambda x: x['score'], reverse=True)
            resultados.append({
                "relato": r,
                "total_matches": len(matches_deste_relato),
                "top_score": matches_deste_relato[0]['score'] if matches_deste_relato else 0,
                "matches": matches_deste_relato[:5]
            })
            
        cursor.close()
        conn.close()
        return jsonify({"success": True, "resultados": resultados})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500
