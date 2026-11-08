"""Documentos administrativos equivalentes na web e no desktop."""
import io
from flask import Blueprint,request,jsonify,send_file,current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.security import secretaria_required
from utils.ferramentas import documento_relatorio,documento_etiquetas,qr_png,id_etiqueta

ferramentas_bp=Blueprint('ferramentas',__name__)
CAMPOS="id,COALESCE(nome_item,descricao) AS nome,descricao AS txt_descricao,categoria,data_encontrado AS txt_data,local_encontrado AS txt_local,status,solicitado_por,rm_aluno"

@ferramentas_bp.route('/api/secretaria/resumo',methods=['GET','OPTIONS'])
@secretaria_required
def resumo():
    """Uma consulta para as prioridades dos dois painéis, sem expor mensagens."""
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""SELECT
          (SELECT count(*) FROM itens WHERE aprovado IS FALSE AND recusado_em IS NULL) AS pendentes,
          (SELECT count(*) FROM itens WHERE aprovado IS NOT FALSE AND status='SOLICITADO') AS retiradas,
          (SELECT count(*) FROM mensagens_chat WHERE remetente='ALUNO' AND NOT lida
             AND criada_em >= CURRENT_TIMESTAMP - INTERVAL '30 days') AS mensagens""")
        return jsonify(success=True,**dict(c.fetchone()))
    except Exception:
        current_app.logger.warning('Resumo administrativo temporariamente indisponível.')
        return jsonify(success=False,message='Não foi possível atualizar as prioridades.'),503
    finally:
        if conn:conn.close()

@ferramentas_bp.route('/api/secretaria/documentos',methods=['GET','OPTIONS'])
@secretaria_required
def documentos():
    conn=None
    try:
        tipo=request.args.get('tipo','INVENTARIO');conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        if tipo=='ENTREGAS':
            c.execute('SELECT id,item_id,nome_item,retirado_por,rm_retirante,turma_curso,data_entrega,funcionario_responsavel,cancelada_em FROM entregues '+('' if request.args.get('revertidas')=='true' else 'WHERE cancelada_em IS NULL ')+'ORDER BY id DESC')
        else:c.execute('SELECT '+CAMPOS+' FROM itens WHERE aprovado IS NOT FALSE ORDER BY id DESC')
        rows=c.fetchall()
        if tipo=='ETIQUETAS':
            id=request.args.get('id')
            if id:
                id=id_etiqueta(id);rows=[i for i in rows if i['id']==id]
                if not rows:return jsonify(success=False,message='Objeto não encontrado.'),404
            else:rows=[i for i in rows if i['status']=='DISPONÍVEL']
            return jsonify(success=True,html=documento_etiquetas(rows),total=len(rows))
        filtros={k:request.args.get(k,'') for k in ['q','categoria','status','local','inicio','fim']}
        return jsonify(success=True,**documento_relatorio(rows,tipo,filtros))
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    except Exception:
        current_app.logger.warning('Documento não pôde ser gerado.')
        return jsonify(success=False,message='Não foi possível gerar o documento. Tente novamente.'),503
    finally:
        if conn:conn.close()

@ferramentas_bp.route('/api/secretaria/etiquetas/<int:item_id>.png',methods=['GET','OPTIONS'])
@secretaria_required
def etiqueta_png(item_id):
    conn=None
    try:
        id_etiqueta(item_id);conn=get_db_connection();c=conn.cursor();c.execute('SELECT 1 FROM itens WHERE id=%s AND aprovado IS NOT FALSE',(item_id,))
        if not c.fetchone():return jsonify(success=False,message='Objeto não encontrado.'),404
        return send_file(io.BytesIO(qr_png(item_id)),mimetype='image/png',as_attachment=True,download_name=f'etiqueta-{item_id}.png')
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    finally:
        if conn:conn.close()

@ferramentas_bp.route('/api/secretaria/etiquetas.png',methods=['GET','OPTIONS'])
@secretaria_required
def folha_png():
    conn=None
    try:
        from utils.ferramentas import folha_etiquetas_png
        pagina=int(request.args.get('pagina','1'));conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT "+CAMPOS+" FROM itens WHERE aprovado IS NOT FALSE AND status='DISPONÍVEL' ORDER BY id DESC")
        rows=c.fetchall();response=send_file(io.BytesIO(folha_etiquetas_png(rows,pagina)),mimetype='image/png',as_attachment=True,download_name=f'etiquetas-pagina-{pagina}.png');response.headers['X-Total-Paginas']=str((len(rows)+14)//15);return response
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    finally:
        if conn:conn.close()
