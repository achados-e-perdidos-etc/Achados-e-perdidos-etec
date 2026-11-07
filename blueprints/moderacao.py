import json
from flask import Blueprint,request,jsonify,current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.security import secretaria_required,token_required,identidade_portal
from utils.evolucao import contextualizar
from utils.privacy import item_publico
from utils.validacao_item import validar_item,validar_categoria
from services.cloudinary_service import processar_fotos,FalhaUploadFotos
from services.moderacao_service import conferir_versao

moderacao_bp=Blueprint('moderacao',__name__)


def falha():
    current_app.logger.warning('Não foi possível consultar ou corrigir o cadastro.')
    return jsonify(success=False,message='Não foi possível concluir. Seus dados foram preservados; tente novamente.'),503


def listar(conectar,paginado=False):
    estado=request.args.get('estado','PENDENTE')
    if estado not in ('PENDENTE','RECUSADO'):return jsonify(success=False,message='Situação de moderação inválida.'),400
    antes=request.args.get('antes')
    if antes is not None and (not antes.isascii() or not antes.isdigit() or not 0<int(antes)<=2147483647):return jsonify(success=False,message='Página inválida.'),400
    conn=None
    try:
        conn=conectar();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('''SELECT id,COALESCE(nome_item,descricao) AS nome,descricao AS txt_descricao,categoria,
         data_encontrado AS txt_data,local_encontrado AS txt_local,foto,fotos_json,status,rm_aluno,
         email_cadastrador,versao,motivo_recusa,recusado_em FROM itens
         WHERE aprovado IS FALSE AND (recusado_em IS NOT NULL)=%s AND (%s::int IS NULL OR id<%s) ORDER BY id DESC LIMIT 201''',(estado=='RECUSADO',antes,antes))
        rows=c.fetchall()
        for row in rows:
            try:row['fotos']=json.loads(row.get('fotos_json') or '[]')
            except (ValueError,TypeError):row['fotos']=[]
        return jsonify(success=True,cadastros=rows[:200],tem_mais=len(rows)>200,proximo=rows[199]['id'] if len(rows)>200 else None) if paginado else jsonify(rows[:200])
    except Exception:return falha()
    finally:
        if conn:conn.close()


@moderacao_bp.route('/api/moderacao/cadastros',methods=['GET','OPTIONS'])
@secretaria_required
def fila():return listar(get_db_connection,paginado=True)


@moderacao_bp.route('/api/meus-cadastros/<int:item_id>',methods=['GET','PUT','OPTIONS'])
@token_required
def corrigir(item_id):
    autor=identidade_portal()
    if not autor:return jsonify(success=False,message='Entre com sua conta do portal.'),403
    conn=None
    try:
        conn=contextualizar(get_db_connection());c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM itens WHERE id=%s AND email_cadastrador=%s'+(' FOR UPDATE' if request.method=='PUT' else ''),(item_id,autor['email']))
        item=c.fetchone()
        if not item:return jsonify(success=False,message='Cadastro não encontrado nesta conta.'),404
        if request.method=='GET':
            dados={**item,'nome':item['nome_item'],'txt_descricao':item['descricao'],'txt_data':item['data_encontrado'],'txt_local':item['local_encontrado']}
            return jsonify(success=True,item={**item_publico(dados),'versao':item['versao'],'motivo_recusa':item['motivo_recusa'],
              'pode_corrigir':item['aprovado'] is False and item['recusado_em'] is not None})
        dados=request.get_json(silent=True)
        try:conferir_versao(dados,item)
        except ValueError as error:return jsonify(success=False,message=str(error)),409
        if item['aprovado'] is not False or item['recusado_em'] is None:
            return jsonify(success=False,message='Só é possível corrigir um cadastro que a secretaria devolveu para ajuste.'),409
        try:
            v=validar_item(dados,item);validar_categoria(get_db_connection,v['categoria'])
        except ValueError as error:return jsonify(success=False,message=str(error)),400
        existentes=item_publico(item)['fotos']
        urls=processar_fotos(dados.get('fotos',existentes),existentes=existentes)
        c.execute('''UPDATE itens SET nome_item=%s,descricao=%s,categoria=%s,data_encontrado=%s,local_encontrado=%s,
         foto=%s,fotos_json=%s,motivo_recusa=NULL,recusado_em=NULL,status='DISPONÍVEL',aprovado=FALSE WHERE id=%s''',
         (v['nome'],v['descricao'],v['categoria'],v['data'],v['local'],urls[0] if urls else '',json.dumps(urls),item_id))
        conn.commit();return jsonify(success=True,message='Cadastro corrigido e reenviado para análise da secretaria.')
    except FalhaUploadFotos as error:
        if conn:conn.rollback()
        return jsonify(success=False,message=str(error)),error.status_code
    except Exception:
        if conn:conn.rollback()
        return falha()
    finally:
        if conn:conn.close()
