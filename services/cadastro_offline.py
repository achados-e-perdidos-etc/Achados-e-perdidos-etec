"""Uma chave por conta e envio: resposta e cadastro confirmados juntos no banco."""
import hashlib
import json
import uuid
from datetime import datetime
from flask import request, jsonify, current_app
from psycopg2.extras import RealDictCursor
from utils.validacao_item import validar_item, validar_categoria, texto
from utils.security import identidade_aluno, identidade_portal
from utils.evolucao import contextualizar
from services.cloudinary_service import processar_fotos, FalhaUploadFotos


def enviar(conectar,tipo,dados):
    try:
        chave=str(uuid.UUID(request.headers.get('Idempotency-Key','')))
        autor=identidade_aluno() if tipo=='mural' else identidade_portal()
        if not autor:return jsonify(success=False,message='Entre na conta que criou o cadastro.'),403
        if not isinstance(dados,dict):raise ValueError('Envie os dados do cadastro.')
        digest=hashlib.sha256(json.dumps(dados,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if tipo=='encontrado':
            valor=validar_item(dados)
        else:
            valor={'categoria':texto(dados.get('categoria'),'Categoria',50).upper(),
                   'descricao':texto(dados.get('descricao'),'Descrição',2000,linhas=True)}
        validar_categoria(conectar,valor['categoria'])
    except (ValueError,TypeError):return jsonify(success=False,message='Confira os campos e a identificação do envio.'),400
    conn=None
    try:
        conn=contextualizar(conectar());c=conn.cursor(cursor_factory=RealDictCursor)
        c.execute('''INSERT INTO requisicoes_portal(email,chave,tipo,hash) VALUES(%s,%s,%s,%s)
         ON CONFLICT(email,chave) DO NOTHING''',(autor['email'],chave,tipo,digest))
        c.execute('SELECT * FROM requisicoes_portal WHERE email=%s AND chave=%s FOR UPDATE',(autor['email'],chave))
        anterior=c.fetchone()
        if anterior['hash']!=digest or anterior['tipo']!=tipo:
            return jsonify(success=False,message='Esta identificação já pertence a outro envio.'),409
        if anterior['resposta'] is not None:return jsonify(anterior['resposta'])
        if tipo=='encontrado':
            urls=processar_fotos(dados.get('fotos') or [])
            c.execute('''INSERT INTO itens(nome_item,descricao,categoria,data_encontrado,local_encontrado,
              foto,fotos_json,status,aprovado,cadastrado_por_aluno,rm_aluno,email_cadastrador)
              VALUES(%s,%s,%s,%s,%s,%s,%s,'DISPONÍVEL',FALSE,TRUE,%s,%s) RETURNING id''',
              (valor['nome'],valor['descricao'],valor['categoria'],valor['data'],valor['local'],
               urls[0] if urls else '',json.dumps(urls),autor['rm'],autor['email']))
        else:
            c.execute('''INSERT INTO mural_perdidos(nome_aluno,rm_aluno,email_aluno,categoria,descricao,data_registro,status)
             VALUES(%s,%s,%s,%s,%s,%s,'PROCURANDO') RETURNING id''',
             (autor['nome'],autor['rm'],autor['email'],valor['categoria'],valor['descricao'],datetime.now().strftime('%d/%m/%Y %H:%M')))
            c.execute("INSERT INTO matches_pendentes(item_id) SELECT id FROM itens WHERE aprovado IS TRUE AND status='DISPONÍVEL' ON CONFLICT DO NOTHING")
        # O INSERT do mural acima não mantém RETURNING depois de enfileirar matches.
        resposta={'success':True,'message':'Cadastro sincronizado.'}
        c.execute('UPDATE requisicoes_portal SET resposta=%s WHERE email=%s AND chave=%s',
                  (json.dumps(resposta),autor['email'],chave));conn.commit()
        return jsonify(resposta)
    except FalhaUploadFotos as error:
        if conn:conn.rollback()
        return jsonify(success=False,message=str(error)),error.status_code
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Sincronização interrompida; a chave de envio pode ser reutilizada.')
        return jsonify(success=False,message='Não foi possível sincronizar. Tente novamente.'),503
    finally:
        if conn:conn.close()
