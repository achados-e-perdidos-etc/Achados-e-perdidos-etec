"""Validação comum antes de processar imagens e persistir itens."""
import re
from datetime import datetime, date


def texto(valor, nome, limite, *, linhas=False):
    if not isinstance(valor, str): raise ValueError(f'{nome} deve ser um texto.')
    valor = valor.strip()
    controles = r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]' if linhas else r'[\x00-\x1f\x7f]'
    if not valor or len(valor) > limite or re.search(controles, valor):
        raise ValueError(f'Informe {nome.lower()} com até {limite} caracteres.')
    return valor


def validar_item(dados, atual=None):
    if not isinstance(dados, dict): raise ValueError('Envie os dados do objeto em JSON.')
    atual = atual or {}
    campos = {
        'nome': ('nome_item', atual.get('descricao', '')[:150] if isinstance(atual.get('descricao'),str) else ''),
        'descricao': ('descricao', ''), 'categoria': ('categoria', 'OUTROS'),
        'data': ('data_encontrado', date.today().strftime('%d/%m/%Y')),
        'local': ('local_encontrado', 'Não informado'), 'status': ('status', 'DISPONÍVEL')
    }
    valores = {k: dados[k] if k in dados else atual.get(col) or padrao for k,(col,padrao) in campos.items()}
    valores['nome'] = texto(valores['nome'],'Título',150)
    valores['descricao'] = texto(valores['descricao'],'Descrição',2000,linhas=True)
    valores['categoria'] = texto(valores['categoria'],'Categoria',50).upper()
    valores['local'] = texto(valores['local'],'Local',100)
    valor_data = texto(valores['data'],'Data',20)
    encontrada = None
    for formato, padrao in [('%d/%m/%Y',r'\d{2}/\d{2}/\d{4}'),('%Y-%m-%d',r'\d{4}-\d{2}-\d{2}')]:
        if re.fullmatch(padrao,valor_data):
            try: encontrada = datetime.strptime(valor_data,formato).date()
            except ValueError: pass
    if encontrada is None or encontrada > date.today(): raise ValueError('Informe uma data válida que não esteja no futuro.')
    valores['data'] = encontrada.strftime('%d/%m/%Y')
    valores['status'] = texto(valores['status'],'Status',30).upper()
    if valores['status'] not in {'DISPONÍVEL','SOLICITADO','ENTREGUE','PARA DOAÇÃO','DOAÇÃO FEITA'}:
        raise ValueError('Situação do objeto inválida.')
    return valores


def validar_categoria(conectar, categoria):
    conn = conectar()
    try:
        c = conn.cursor()
        c.execute('SELECT 1 FROM categorias WHERE UPPER(nome)=%s;', (categoria,))
        if not c.fetchone(): raise ValueError('Escolha uma categoria cadastrada.')
    finally: conn.close()
