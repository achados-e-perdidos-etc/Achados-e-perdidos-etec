"""Moderação preserva cadastro e motivo; decisões e correções usam versão da linha."""
import json
from flask import request,jsonify,current_app
from psycopg2.extras import RealDictCursor
from utils.validacao_item import texto
from utils.evolucao import contextualizar
from services.catalogo_service import duplicados


def conferir_versao(dados,item):
    if not isinstance(dados,dict) or type(dados.get('versao')) is not int or dados['versao']!=item.get('versao'):
        raise ValueError('Este cadastro mudou. Atualize os dados antes de decidir.')


def aviso_duplicado(cursor,dados,excluir=None):
    candidatos=duplicados(cursor,dados,excluir)
    if candidatos and dados.get('confirmar_duplicado') is not True:
        return jsonify(success=False,code='POSSIVEL_DUPLICADO',message='Há objetos parecidos. Confira antes de publicar.',duplicados=candidatos),409
    return None


def registrar_revisao(cursor,item_id,dados):
    if dados.get('confirmar_duplicado') is True:
        cursor.execute('''INSERT INTO ocorrencias_itens(item_id,acao,ator_id,perfil,atual)
          VALUES(%s,'REV_DUPLIC',%s,%s,%s)''',(item_id,request.user['email'],request.user.get('perfil') or request.user['role'],json.dumps({'revisao':'Possível duplicidade conferida antes da publicação.'})))


def aprovar(conectar,item_id):
    conn=None
    try:
        dados=request.get_json(silent=True) or {}
        conn=contextualizar(conectar());c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM itens WHERE id=%s FOR UPDATE',(item_id,));item=c.fetchone()
        if not item:return jsonify(success=False,message='Cadastro não encontrado.'),404
        try:conferir_versao(dados,item)
        except ValueError as error:return jsonify(success=False,message=str(error)),409
        if item['aprovado'] is not False:return jsonify(success=False,message='Este cadastro já saiu da moderação.'),409
        origem={'nome':item.get('nome_item') or item['descricao'],'categoria':item['categoria'],'data':item['data_encontrado'],**{'confirmar_duplicado':dados.get('confirmar_duplicado')}}
        aviso=aviso_duplicado(c,origem,item_id)
        if aviso:return aviso
        c.execute('UPDATE itens SET aprovado=TRUE,motivo_recusa=NULL,recusado_em=NULL WHERE id=%s',(item_id,))
        registrar_revisao(c,item_id,dados);conn.commit()
        return jsonify(success=True,message='Objeto aprovado no catálogo.')
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Não foi possível aprovar o cadastro.')
        return jsonify(success=False,message='Aprovação não confirmada. Atualize e tente novamente.'),503
    finally:
        if conn:conn.close()


def recusar_com_cursor(cursor,item_id,item,dados):
    try:
        conferir_versao(dados,item)
        motivo=texto(dados.get('motivo'),'Motivo da recusa',1000,linhas=True)
        if len(motivo)<5:raise ValueError('Explique a recusa com pelo menos cinco caracteres.')
    except ValueError as error:return jsonify(success=False,message=str(error)),409 if 'mudou' in str(error) else 400
    cursor.execute('UPDATE itens SET motivo_recusa=%s,recusado_em=CURRENT_TIMESTAMP WHERE id=%s',(motivo,item_id))
    return None


def publicar_conferido(conectar,dados,excluir=None):
    """Verifica somente metadados antes de enviar fotos de um cadastro da equipe."""
    conn=conectar()
    try:
        c=conn.cursor(cursor_factory=RealDictCursor)
        return aviso_duplicado(c,dados,excluir)
    finally:conn.close()
