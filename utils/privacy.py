"""Projeções explícitas para as consultas públicas do catálogo e do mural."""
import json

ITEM_FIELDS = ('id', 'nome', 'txt_descricao', 'categoria', 'txt_data', 'txt_local',
               'foto', 'fotos_json', 'fotos', 'status', 'aprovado', 'cadastrado_por_aluno')
MURAL_FIELDS = ('id', 'categoria', 'descricao', 'data_registro', 'status')

def item_publico(item):
    result = {key: item[key] for key in ITEM_FIELDS if key in item}
    if 'fotos' not in result:
        try:
            result['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else []
        except (ValueError, TypeError):
            result['fotos'] = []
        if not result['fotos'] and item.get('foto'):
            result['fotos'] = [item['foto']]
    return result

def relato_publico(relato):
    result = {key: relato[key] for key in MURAL_FIELDS if key in relato}
    result['nome_aluno'] = 'Aluno'
    return result
