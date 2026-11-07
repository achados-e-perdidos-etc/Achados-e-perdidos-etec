"""Retirada presencial com código, comprovante privado e consulta de auditoria."""
import hashlib
import hmac
import io
import re
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, send_file
from psycopg2.extras import RealDictCursor
from config import JWT_SECRET
from database import get_db_connection
from utils.security import token_required, secretaria_required, identidade_aluno
from utils.evolucao import contextualizar
from utils.entregas import registrar_entrega
from utils.imagens import preparar_imagem

evolucao_bp = Blueprint('evolucao', __name__)


def codigo_do_registro(row):
    material = f"retirada-v1:{row['item_id']}:{row['email']}:{row['nonce']}".encode()
    digest = hmac.new(JWT_SECRET.encode(), material, hashlib.sha256).digest()
    return str(int.from_bytes(digest[:8], 'big') % 1000000).zfill(6)


def falha():
    current_app.logger.warning('Não foi possível concluir a operação de retirada/auditoria.')
    return jsonify(success=False, message='Operação indisponível. Atualize os dados e tente novamente.'), 503


@evolucao_bp.route('/api/retiradas/<int:item_id>/codigo', methods=['POST', 'OPTIONS'])
@token_required
def emitir_codigo(item_id):
    aluno = identidade_aluno()
    if not aluno: return jsonify(success=False, message='Use a conta do aluno que solicitou o objeto.'), 403
    conn = None
    try:
        conn = contextualizar(get_db_connection()); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT status,aprovado,email_solicitante FROM itens WHERE id=%s FOR UPDATE', (item_id,))
        item = c.fetchone()
        if not item or item['email_solicitante'] != aluno['email']:
            return jsonify(success=False, message='Solicitação não encontrada.'), 404
        if item['status'] != 'SOLICITADO' or item['aprovado'] is not True:
            return jsonify(success=False, message='Este objeto não está aguardando retirada.'), 409
        c.execute('''INSERT INTO retiradas_codigos(item_id,email,nonce,expira_em)
          VALUES(%s,%s,%s,CURRENT_TIMESTAMP+INTERVAL '15 minutes')
          ON CONFLICT(item_id) DO UPDATE SET email=EXCLUDED.email,nonce=EXCLUDED.nonce,
           expira_em=EXCLUDED.expira_em,tentativas=0,usado_em=NULL,requisicao=NULL,responsavel=NULL
          WHERE retiradas_codigos.email<>EXCLUDED.email OR retiradas_codigos.expira_em<=CURRENT_TIMESTAMP
          OR retiradas_codigos.usado_em IS NOT NULL''', (item_id,aluno['email'],str(uuid.uuid4())))
        c.execute('SELECT * FROM retiradas_codigos WHERE item_id=%s', (item_id,)); row = c.fetchone()
        if row['tentativas'] >= 5:
            return jsonify(success=False, message='Código bloqueado. Aguarde a validade terminar para gerar outro.'), 429
        conn.commit()
        return jsonify(success=True, codigo=codigo_do_registro(row), expira_em=row['expira_em'].isoformat(), item_id=item_id,
          aviso='Apresente o código e confirme seus dados com a secretaria. Ele não comprova a propriedade do objeto.')
    except Exception:
        if conn: conn.rollback()
        return falha()
    finally:
        if conn: conn.close()


def verificar_codigo(cursor, item_id, codigo):
    cursor.execute('SELECT *,expira_em>CURRENT_TIMESTAMP AS valido FROM retiradas_codigos WHERE item_id=%s FOR UPDATE', (item_id,))
    row = cursor.fetchone()
    if not row or not row['valido'] or row['usado_em'] is not None or row['tentativas'] >= 5:
        return row, False
    if not hmac.compare_digest(codigo_do_registro(row), codigo):
        cursor.execute('UPDATE retiradas_codigos SET tentativas=tentativas+1 WHERE item_id=%s', (item_id,))
        return row, False
    return row, True


@evolucao_bp.route('/api/retiradas/<int:item_id>/confirmar', methods=['POST', 'OPTIONS'])
@secretaria_required
def confirmar(item_id):
    dados = request.get_json(silent=True)
    if not isinstance(dados,dict) or not re.fullmatch(r'[0-9]{6}', str(dados.get('codigo') or '')):
        return jsonify(success=False, message='Informe o código de seis dígitos.'), 400
    try: chave = str(uuid.UUID(str(dados.get('requisicao'))))
    except (ValueError, TypeError): return jsonify(success=False, message='Atualize a tela de retirada.'), 400
    if dados.get('identidade_conferida') is not True:
        return jsonify(success=False, message='Confira presencialmente a identidade e os detalhes do objeto.'), 400
    try: assinatura = preparar_imagem(dados.get('assinatura'), lado=700, limite=128*1024)
    except ValueError:
        return jsonify(success=False, message='Peça ao aluno para assinar o recebimento na tela.'), 400
    conn = None
    try:
        conn = contextualizar(get_db_connection()); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM itens WHERE id=%s FOR UPDATE', (item_id,)); item = c.fetchone()
        if not item: return jsonify(success=False, message='Objeto não encontrado.'), 404
        row, valido = verificar_codigo(c,item_id,dados['codigo'])
        if row and row['usado_em'] and str(row['requisicao']) == chave and row['responsavel'] == request.user['email']:
            return jsonify(success=True, message='Entrega já confirmada.', repetida=True)
        if not valido:
            conn.commit()
            return jsonify(success=False, message='Código inválido, bloqueado, utilizado ou expirado.'), 409
        if item['status'] != 'SOLICITADO' or item['aprovado'] is not True or item['email_solicitante'] != row['email']:
            return jsonify(success=False, message='A solicitação mudou. Atualize a tela.'), 409
        c.execute("UPDATE itens SET status='ENTREGUE' WHERE id=%s", (item_id,))
        registrar_entrega(c,item_id,item.get('nome_item') or item['descricao'],{},item,request.user['email'])
        c.execute("""UPDATE entregues SET assinatura=%s,confirmada_em=CURRENT_TIMESTAMP,metodo='CODIGO'
          WHERE item_id=%s AND cancelada_em IS NULL RETURNING id""", (assinatura,item_id))
        recibo = c.fetchone()['id']
        c.execute('UPDATE retiradas_codigos SET usado_em=CURRENT_TIMESTAMP,requisicao=%s,responsavel=%s WHERE item_id=%s',
                  (chave,request.user['email'],item_id))
        conn.commit()
        from services.push_delivery import notificar
        notificar(row['email'],'item')
        return jsonify(success=True, comprovante_id=recibo, message='Entrega confirmada e comprovante registrado.')
    except Exception:
        if conn: conn.rollback()
        return falha()
    finally:
        if conn: conn.close()


@evolucao_bp.route('/api/retiradas/comprovantes/<int:recibo>', methods=['GET', 'OPTIONS'])
@secretaria_required
def consultar_recibo(recibo):
    conn = None
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('''SELECT id,item_id,nome_item,retirado_por,rm_retirante,turma_curso,data_entrega,
         funcionario_responsavel,metodo,cancelada_em,cancelada_por,
         (assinatura IS NOT NULL) AS tem_assinatura FROM entregues WHERE id=%s''',(recibo,))
        row=c.fetchone()
        if not row:return jsonify(success=False,message='Comprovante não encontrado.'),404
        if row.get('cancelada_em'):row['cancelada_em']=row['cancelada_em'].isoformat()
        return jsonify(success=True,comprovante=row)
    except Exception:return falha()
    finally:
        if conn:conn.close()


@evolucao_bp.route('/api/retiradas/comprovantes/<int:recibo>/assinatura', methods=['GET', 'OPTIONS'])
@secretaria_required
def assinatura_recibo(recibo):
    conn = None
    try:
        conn=get_db_connection(); c=conn.cursor()
        c.execute('SELECT assinatura FROM entregues WHERE id=%s', (recibo,)); row=c.fetchone()
        if not row or not row[0]: return jsonify(success=False, message='Assinatura indisponível.'),404
        response=send_file(io.BytesIO(bytes(row[0])),mimetype='image/jpeg',max_age=0)
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    except Exception: return falha()
    finally:
        if conn: conn.close()


@evolucao_bp.route('/api/itens/<int:item_id>/ocorrencias', methods=['GET', 'OPTIONS'])
@secretaria_required
def ocorrencias(item_id):
    try: antes=int(request.args.get('antes','9223372036854775807'))
    except ValueError: return jsonify(success=False,message='Página inválida.'),400
    if not 0<antes<=9223372036854775807:return jsonify(success=False,message='Página inválida.'),400
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM ocorrencias_itens WHERE item_id=%s AND id<%s ORDER BY id DESC LIMIT 51',(item_id,antes))
        rows=c.fetchall()
        nomes={'nome':'Título','descricao':'Descrição','categoria':'Categoria','local':'Local','data':'Data encontrada',
          'status':'Situação','aprovado':'Aprovação','fotos':'Fotos','motivo_recusa':'Motivo da recusa','revisao':'Conferência de duplicidade'}
        for row in rows[:50]:
            antes=row.get('anterior') or {};depois=row.get('atual') or {}
            row['alteracoes']=[dict(campo=nome,chave=chave,antes=antes.get(chave),depois=depois.get(chave))
              for chave,nome in nomes.items() if antes.get(chave)!=depois.get(chave)]
        return jsonify(success=True,ocorrencias=rows[:50],tem_mais=len(rows)>50)
    except Exception:return falha()
    finally:
        if conn:conn.close()
