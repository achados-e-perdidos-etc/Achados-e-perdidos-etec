from flask import Blueprint,jsonify,request,current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection,verificar_e_atualizar_itens_doacao
from utils.security import consulta_publica,secretaria_required
from utils.privacy import item_publico
from services.catalogo_service import pagina,duplicados,CAMPOS,preparar_publico

catalogo_bp=Blueprint('catalogo',__name__)

@catalogo_bp.route('/api/catalogo',methods=['GET','OPTIONS'])
@consulta_publica
def listar():
    conn=None
    try:
        verificar_e_atualizar_itens_doacao()
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        return jsonify(pagina(c,request.args))
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    except Exception:
        current_app.logger.warning('O catálogo não pôde ser carregado.')
        return jsonify(success=False,message='Não foi possível carregar o catálogo. Tente novamente.'),503
    finally:
        if conn:conn.close()

@catalogo_bp.route('/api/catalogo/<int:item_id>',methods=['GET','OPTIONS'])
@consulta_publica
def detalhe(item_id):
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT '+CAMPOS+' FROM itens WHERE id=%s AND aprovado IS NOT FALSE',(item_id,));row=c.fetchone()
        if not row:return jsonify(success=False,message='Objeto não encontrado no catálogo.'),404
        return jsonify(success=True,item=preparar_publico(row))
    except Exception:
        current_app.logger.warning('O objeto não pôde ser consultado.')
        return jsonify(success=False,message='Não foi possível consultar o objeto. Tente novamente.'),503
    finally:
        if conn:conn.close()

@catalogo_bp.route('/api/itens/duplicados',methods=['POST','OPTIONS'])
@secretaria_required
def conferir_duplicados():
    conn=None
    try:
        dados=request.get_json(silent=True);excluir=dados.get('id') if isinstance(dados,dict) else None
        if excluir is not None and (isinstance(excluir,bool) or not str(excluir).isascii() or not str(excluir).isdigit() or not 0<int(excluir)<=2147483647):raise ValueError('Objeto inválido.')
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        return jsonify(success=True,duplicados=duplicados(c,dados,int(excluir) if excluir else None))
    except ValueError as error:return jsonify(success=False,message=str(error)),400
    except Exception:
        current_app.logger.warning('Não foi possível conferir possíveis duplicados.')
        return jsonify(success=False,message='Não foi possível conferir duplicidade. Tente novamente antes de publicar.'),503
    finally:
        if conn:conn.close()
