from flask import request, jsonify, current_app
from psycopg2.extras import RealDictCursor
from utils.entregas import cancelar_entregas
from services import push_delivery


def reverter(conectar, item_id):
    conn = None
    try:
        conn = conectar();c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM itens WHERE id=%s FOR UPDATE;', (item_id,))
        item = c.fetchone()
        if not item: return jsonify(success=False,message='Item não encontrado.'),404
        dados=request.get_json(silent=True) or {}
        recibo=dados.get('entrega_id') if isinstance(dados,dict) else None
        if recibo is not None:
            if isinstance(recibo,bool) or not str(recibo).isascii() or not str(recibo).isdigit() or not 0<int(recibo)<2147483648:
                return jsonify(success=False,message='Comprovante inválido.'),400
            c.execute('SELECT 1 FROM entregues WHERE id=%s AND item_id=%s AND cancelada_em IS NULL',(int(recibo),item_id))
            if not c.fetchone():return jsonify(success=False,message='Esta entrega já mudou. Atualize o histórico.'),409
        if item['aprovado'] is False:
            from services.moderacao_service import recusar_com_cursor
            erro=recusar_com_cursor(c,item_id,item,dados)
            if erro:return erro
            mensagem = 'Cadastro devolvido para correção, com motivo registrado.'
        else:
            cancelar_entregas(c,item_id,request.user['email'])
            c.execute("UPDATE itens SET status='DISPONÍVEL',solicitado_por=NULL,rm_aluno=NULL,email_solicitante=NULL WHERE id=%s;", (item_id,))
            mensagem = 'Item disponível. Entregas anteriores foram preservadas como canceladas.'
        conn.commit()
        push_delivery.notificar(item.get('email_solicitante'),'item')
        return jsonify(success=True,message=mensagem)
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Não foi possível concluir a reversão do item.')
        return jsonify(success=False,message='Não foi possível reverter. Atualize os dados antes de tentar novamente.'),503
    finally:
        if conn:conn.close()
