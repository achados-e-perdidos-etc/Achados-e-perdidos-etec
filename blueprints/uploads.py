import hashlib,io,re,uuid
from flask import Blueprint,request,jsonify,current_app
from psycopg2.extras import RealDictCursor
from PIL import Image
import cloudinary.uploader
from database import get_db_connection
from utils.security import token_required,identidade_portal

uploads_bp=Blueprint('uploads',__name__)

@uploads_bp.route('/api/uploads',methods=['POST','OPTIONS'])
@uploads_bp.route('/api/uploads/<uuid:upload_id>',methods=['GET','PUT','DELETE','OPTIONS'])
@uploads_bp.route('/api/uploads/<uuid:upload_id>/parte',methods=['POST','OPTIONS'])
@uploads_bp.route('/api/uploads/<uuid:upload_id>/finalizar',methods=['POST','OPTIONS'])
@token_required
def upload(upload_id=None):
    if request.user.get('role')!='secretaria' and not identidade_portal():return jsonify(success=False,message='Entre em sua conta.'),403
    email=request.user.get('email');conn=None
    if not email:return jsonify(success=False),403
    dados=request.get_json(silent=True) if upload_id is None else None
    if upload_id is None and (not isinstance(dados,dict) or type(dados.get('tamanho')) is not int or not 0<dados['tamanho']<=2*1024*1024 or not isinstance(dados.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',dados['sha256'])):
        return jsonify(success=False,message='Foto inválida ou maior que 2 MB.'),400
    try:
        conn=get_db_connection();c=conn.cursor(cursor_factory=RealDictCursor)
        if upload_id is None:
            c.execute('SELECT pg_advisory_xact_lock(281030002);')
            c.execute("DELETE FROM uploads_fotos WHERE atualizado_em<CURRENT_TIMESTAMP-INTERVAL '24 hours'")
            if dados.get('retomar') is True:
                c.execute('SELECT id,recebidos,url FROM uploads_fotos WHERE email=%s AND sha256=%s AND tamanho=%s ORDER BY atualizado_em DESC LIMIT 1',(email,dados['sha256'],dados['tamanho']))
                existente=c.fetchone()
                if existente:
                    c.execute('UPDATE uploads_fotos SET atualizado_em=CURRENT_TIMESTAMP WHERE id=%s',(str(existente['id']),));conn.commit()
                    return jsonify(success=True,id=str(existente['id']),recebidos=existente['recebidos'],url=existente['url'])
            c.execute("SELECT COALESCE(SUM(tamanho),0) AS total FROM uploads_fotos WHERE url IS NULL AND atualizado_em>=CURRENT_TIMESTAMP-INTERVAL '24 hours'")
            if c.fetchone()['total']+dados['tamanho']>32*1024*1024:return jsonify(success=False,message='Há muitos envios em andamento. Aguarde e tente novamente.'),429
            c.execute("DELETE FROM uploads_fotos WHERE email=%s AND atualizado_em<CURRENT_TIMESTAMP-INTERVAL '24 hours'",(email,))
            c.execute('SELECT COUNT(*) AS total FROM uploads_fotos WHERE email=%s AND url IS NULL',(email,))
            if c.fetchone()['total']>=4:return jsonify(success=False,message='Conclua as fotos pendentes antes de enviar outras.'),429
            upload_id=uuid.uuid4()
            c.execute('INSERT INTO uploads_fotos (id,email,tamanho,sha256) VALUES (%s,%s,%s,%s)',(str(upload_id),email,dados['tamanho'],dados['sha256']))
            conn.commit();return jsonify(success=True,id=str(upload_id),recebidos=0),201
        c.execute("SELECT * FROM uploads_fotos WHERE id=%s AND email=%s AND atualizado_em>=CURRENT_TIMESTAMP-INTERVAL '24 hours' FOR UPDATE",(str(upload_id),email))
        row=c.fetchone()
        if not row:return jsonify(success=False,message='Envio expirado ou não encontrado.'),404
        if request.method=='DELETE':
            c.execute('DELETE FROM uploads_fotos WHERE id=%s',(str(upload_id),));conn.commit();return jsonify(success=True)
        if request.method=='PUT' or request.path.endswith('/parte'):
            try:offset=int(request.headers.get('X-Upload-Offset','-1'))
            except ValueError:offset=-1
            if offset!=row['recebidos']:return jsonify(success=False,recebidos=row['recebidos']),409
            chunk=request.get_data()
            if row['url'] or not 0<len(chunk)<=65536 or offset+len(chunk)>row['tamanho']:return jsonify(success=False,message='Parte da foto inválida.'),400
            c.execute('INSERT INTO uploads_partes (upload_id,posicao,conteudo) VALUES (%s,%s,%s)',(str(upload_id),offset,chunk))
            c.execute('UPDATE uploads_fotos SET recebidos=recebidos+%s,atualizado_em=CURRENT_TIMESTAMP WHERE id=%s',(len(chunk),str(upload_id)))
            conn.commit();return jsonify(success=True,recebidos=offset+len(chunk))
        if request.method=='POST' and not row['url']:
            if row['recebidos']!=row['tamanho']:return jsonify(success=False,message='O envio da foto ainda não terminou.'),409
            c.execute('SELECT conteudo FROM uploads_partes WHERE upload_id=%s ORDER BY posicao',(str(upload_id),))
            data=b''.join(bytes(p['conteudo']) for p in c.fetchall())
            if hashlib.sha256(data).hexdigest()!=row['sha256']:return jsonify(success=False,message='A foto recebida não confere.'),400
            try:
                with Image.open(io.BytesIO(data)) as foto:
                    if foto.format not in ['JPEG','PNG','WEBP']:raise ValueError()
                    foto.verify()
            except Exception:return jsonify(success=False,message='Arquivo de imagem inválido.'),400
            resultado=cloudinary.uploader.upload(io.BytesIO(data),public_id='etec_achados/'+str(upload_id),overwrite=True,resource_type='image',timeout=30)
            url=resultado.get('secure_url')
            if not isinstance(url,str) or not url.startswith('https://'):raise ValueError()
            c.execute("UPDATE uploads_fotos SET url=%s,atualizado_em=CURRENT_TIMESTAMP WHERE id=%s",(url,str(upload_id)))
            c.execute('DELETE FROM uploads_partes WHERE upload_id=%s',(str(upload_id),))
            conn.commit();row['url']=url
        return jsonify(success=True,id=str(upload_id),recebidos=row['recebidos'],url=row['url'])
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Envio de foto interrompido; partes confirmadas preservadas.')
        return jsonify(success=False,message='Não foi possível concluir esta foto. Tente novamente.'),503
    finally:
        if conn:conn.close()
