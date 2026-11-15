"""A foto é visível apenas ao titular e à equipe administrativa autenticada."""
import io,uuid
from flask import Blueprint,request,jsonify,send_file,current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.security import token_required,secretaria_required,identidade_portal
from utils.perfis import VERSAO_TERMOS,SECOES_TERMOS
from services.foto_perfil import preparar_foto

perfis_bp=Blueprint('perfis',__name__)


@perfis_bp.route('/api/termos',methods=['GET'])
def termos():return jsonify(success=True,versao=VERSAO_TERMOS,url='/termos',secoes=[dict(titulo=t,texto=p) for t,p in SECOES_TERMOS])


@perfis_bp.route('/termos',methods=['GET'])
def documento_termos():
    from html import escape
    texto=''.join('<section><h2>'+escape(t)+'</h2><p>'+escape(p)+'</p></section>' for t,p in SECOES_TERMOS)
    return '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Termos de Uso</title><style>body{font:16px/1.8 system-ui;background:#f5f6fa;color:#192334;margin:0}main{max-width:780px;margin:auto;padding:24px}h1{font-size:30px}h2{font-size:21px}section{margin:28px 0}a{color:#a51626}</style><main><h1>Termos de Uso e informações sobre dados</h1><p>Versão '+escape(VERSAO_TERMOS)+'</p>'+texto+'<a href="/">Voltar ao portal</a></main></html>'


def consultar(email=None,item_id=None):
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        alvo='(SELECT email_solicitante FROM itens WHERE id=%s AND status=\'SOLICITADO\')' if item_id is not None else '%s'
        c.execute('SELECT a.nome,a.email,a.rm,p.id AS foto_id FROM alunos a LEFT JOIN perfis_fotos p ON p.email=a.email WHERE a.email='+alvo,(item_id if item_id is not None else email,));row=c.fetchone()
        if not row:return jsonify(success=False,message='Conta não encontrada.'),404
        if row['foto_id']:row['foto_id']=str(row['foto_id'])
        return jsonify(success=True,perfil=row)
    except Exception:
        current_app.logger.warning('Consulta de perfil indisponível.');return jsonify(success=False,message='Não foi possível consultar o perfil.'),503
    finally:
        if conn:conn.close()


@perfis_bp.route('/api/perfil',methods=['GET','OPTIONS'])
@token_required
def proprio():return consultar(request.user['email'])


@perfis_bp.route('/api/secretaria/perfil',methods=['POST','OPTIONS'])
@secretaria_required
def aluno():
    d=request.get_json(silent=True)
    if isinstance(d,dict) and type(d.get('item_id')) is int and 0<d['item_id']<2147483648:return consultar(item_id=d['item_id'])
    if not isinstance(d,dict) or not isinstance(d.get('email'),str) or not 1<len(d['email'].strip())<=150:return jsonify(success=False,message='Selecione a conta do aluno ou informe o número do objeto solicitado.'),400
    return consultar(d['email'].strip().lower())


@perfis_bp.route('/api/perfil/foto',methods=['POST','DELETE','OPTIONS'])
@token_required
def alterar():
    conta=identidade_portal()
    if not conta:return jsonify(success=False,message='Entre com sua conta de aluno ou professor.'),403
    foto=None
    if request.method=='POST':
        d=request.get_json(silent=True)
        if not isinstance(d,dict):return jsonify(success=False,message='Selecione uma foto.'),400
        try:foto=preparar_foto(d.get('foto'))
        except ValueError as e:return jsonify(success=False,message=str(e)),400
        except RuntimeError as e:return jsonify(success=False,message=str(e)),503
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor()
        if request.method=='DELETE':c.execute('DELETE FROM perfis_fotos WHERE email=%s',(conta['email'],));foto_id=None
        else:
            foto_id=str(uuid.uuid4())
            c.execute('''INSERT INTO perfis_fotos(email,id,foto) VALUES(%s,%s,%s)
             ON CONFLICT(email) DO UPDATE SET id=EXCLUDED.id,foto=EXCLUDED.foto,atualizado_em=CURRENT_TIMESTAMP''',(conta['email'],foto_id,foto))
        conn.commit();return jsonify(success=True,foto_id=foto_id,message='Foto atualizada.' if foto else 'Foto removida.')
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Não foi possível alterar a foto de perfil.');return jsonify(success=False,message='Não foi possível salvar sua foto. Tente novamente.'),503
    finally:
        if conn:conn.close()


@perfis_bp.route('/api/perfil/foto/<uuid:foto_id>',methods=['GET','OPTIONS'])
@token_required
def imagem(foto_id):
    conn=None
    try:
        conn=get_db_connection();c=conn.cursor()
        c.execute('SELECT foto FROM perfis_fotos WHERE id=%s AND (email=%s OR %s)',(str(foto_id),request.user['email'],request.user.get('role')=='secretaria'));row=c.fetchone()
        if not row:return jsonify(success=False,message='Foto indisponível.'),404
        response=send_file(io.BytesIO(bytes(row[0])),mimetype='image/jpeg',max_age=0)
        response.headers['Cache-Control']='private, no-store';return response
    except Exception:
        current_app.logger.warning('Foto privada temporariamente indisponível.');return jsonify(success=False,message='Foto indisponível.'),503
    finally:
        if conn:conn.close()
