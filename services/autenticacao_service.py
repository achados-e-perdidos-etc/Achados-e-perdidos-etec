"""Códigos de uso único, limites por conta e revogação compartilhada no PostgreSQL."""
import hashlib,hmac,secrets,time
from datetime import datetime,timedelta
from flask import request,jsonify,current_app
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash,check_password_hash
from config import JWT_SECRET
from utils.helpers import validar_email_institucional

SCHEMA_AUTH='''
ALTER TABLE codigos_auth ALTER COLUMN codigo TYPE VARCHAR(128);
ALTER TABLE codigos_auth ADD COLUMN IF NOT EXISTS finalidade VARCHAR(20) NOT NULL DEFAULT 'cadastro';
ALTER TABLE codigos_auth ADD COLUMN IF NOT EXISTS tentativas INTEGER NOT NULL DEFAULT 0;
ALTER TABLE codigos_auth ADD COLUMN IF NOT EXISTS enviado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
DELETE FROM codigos_auth WHERE codigo !~ '^[a-f0-9]{64}$';
CREATE TABLE IF NOT EXISTS auth_limites(chave VARCHAR(64) PRIMARY KEY,janela TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,quantidade INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS auth_limites_janela ON auth_limites(janela);
CREATE TABLE IF NOT EXISTS auth_revogacoes(email VARCHAR(150) PRIMARY KEY,desde DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS auth_tokens_revogados(jti VARCHAR(64) PRIMARY KEY,expira_em DOUBLE PRECISION NOT NULL);
CREATE INDEX IF NOT EXISTS auth_tokens_expiracao ON auth_tokens_revogados(expira_em);
'''
DUMMY_HASH=generate_password_hash('credencial-inexistente-'+secrets.token_hex(16))


def resumo_codigo(email,finalidade,codigo):
    return hmac.new(JWT_SECRET.encode(),(email+'\0'+finalidade+'\0'+codigo).encode(),hashlib.sha256).hexdigest()


def limitar(c,email,operacao,maximo):
    chave=resumo_codigo(email,'limite',operacao)
    c.execute("DELETE FROM auth_limites WHERE janela<CURRENT_TIMESTAMP-INTERVAL '1 day'")
    c.execute('''INSERT INTO auth_limites(chave) VALUES(%s) ON CONFLICT(chave) DO UPDATE SET
      quantidade=CASE WHEN auth_limites.janela<CURRENT_TIMESTAMP-INTERVAL '15 minutes' THEN 1 ELSE auth_limites.quantidade+1 END,
      janela=CASE WHEN auth_limites.janela<CURRENT_TIMESTAMP-INTERVAL '15 minutes' THEN CURRENT_TIMESTAMP ELSE auth_limites.janela END
      RETURNING quantidade''',(chave,))
    return c.fetchone()['quantidade']<=maximo


def senha_valida(senha):return isinstance(senha,str) and 12<=len(senha)<=128 and len(senha.encode())<=512 and '\x00' not in senha


def sessao_valida(payload):
    from database import get_db_connection
    conn=get_db_connection()
    try:
        c=conn.cursor();c.execute('''SELECT EXISTS(SELECT 1 FROM auth_revogacoes WHERE email=%s AND desde>=%s)
         OR EXISTS(SELECT 1 FROM auth_tokens_revogados WHERE jti=%s)''',(payload['email'],payload['iat'],payload['jti']))
        return not c.fetchone()[0]
    finally:conn.close()


def sair(conectar):
    conn=conectar()
    try:
        c=conn.cursor();c.execute('DELETE FROM auth_tokens_revogados WHERE expira_em<%s',(time.time(),))
        c.execute('INSERT INTO auth_tokens_revogados(jti,expira_em) VALUES(%s,%s) ON CONFLICT DO NOTHING',(request.user['jti'],request.user['exp']+60))
        conn.commit();return jsonify(success=True)
    finally:conn.close()


def verificar_codigo(c,email,finalidade,codigo):
    c.execute('SELECT codigo,expiracao,finalidade,tentativas FROM codigos_auth WHERE email=%s FOR UPDATE',(email,));reg=c.fetchone()
    if not reg or reg['finalidade']!=finalidade or reg['expiracao']<datetime.now() or reg['tentativas']>=5:return False
    valido=isinstance(codigo,str) and len(codigo)==6 and codigo.isascii() and codigo.isdigit() and hmac.compare_digest(reg['codigo'],resumo_codigo(email,finalidade,codigo))
    if not valido:c.execute('UPDATE codigos_auth SET tentativas=tentativas+1 WHERE email=%s',(email,))
    return valido


def operar(acao,conectar):
    from utils.perfis import validar_aceite,registrar_aceite
    from utils.security import gerar_token_aluno
    d=request.get_json(silent=True)
    if not isinstance(d,dict):return jsonify(success=False,message='Envie os campos em um objeto JSON válido.'),400
    if acao=='cadastrar':
        erro=validar_aceite(d)
        if erro:return jsonify(success=False,message=erro),400
    valido,email=validar_email_institucional(d.get('email'))
    if not valido or len(email)>150:return jsonify(success=False,message='Credenciais incorretas.' if acao=='login' else 'Informe seu e-mail institucional válido.'),(401 if acao=='login' else 400)
    senha=d.get('senha');finalidade=d.get('finalidade','cadastro')
    if acao=='enviar' and finalidade not in ('cadastro','recuperacao'):return jsonify(success=False,message='Solicitação inválida.'),400
    if acao in ('cadastrar','redefinir') and not senha_valida(senha):return jsonify(success=False,message='Use uma senha com 12 a 128 caracteres.'),400
    if acao=='login' and (not isinstance(senha,str) or not 1<=len(senha)<=128):return jsonify(success=False,message='Credenciais incorretas.'),401
    nome,rm=d.get('nome'),d.get('rm')
    if acao=='cadastrar':
        if not isinstance(nome,str) or not 2<=len(nome.strip())<=100 or any(ord(x)<32 for x in nome):return jsonify(success=False,message='Informe seu nome completo, com até 100 caracteres.'),400
        if email.endswith(('@cps.sp.gov.br','@etec.sp.gov.br')):rm='PROFESSOR'
        elif not isinstance(rm,str) or not 3<=len(rm.strip())<=20 or not rm.strip().isascii() or not rm.strip().isdigit():return jsonify(success=False,message='Informe seu RM numérico, com até 20 dígitos.'),400
        nome=nome.strip();rm=rm.strip()
    conn=None
    try:
        conn=conectar();c=conn.cursor(cursor_factory=RealDictCursor)
        if acao=='enviar':
            # Trava por conta antes de emitir/substituir códigos, inclusive em vários workers.
            c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(email,))
            if not limitar(c,email,'enviar',3):conn.commit();return jsonify(success=False,message='Aguarde 15 minutos antes de solicitar outro código.'),429
            c.execute("SELECT 1 FROM codigos_auth WHERE email=%s AND enviado_em>CURRENT_TIMESTAMP-INTERVAL '60 seconds'",(email,))
            if c.fetchone():conn.commit();return jsonify(success=False,message='Aguarde um minuto antes de pedir outro código.'),429
            c.execute('SELECT email FROM alunos WHERE email=%s',(email,));existe=bool(c.fetchone())
            resposta=dict(success=True,message='Se a solicitação puder ser atendida, você receberá um código no e-mail institucional.')
            if existe!=(finalidade=='recuperacao'):conn.commit();return jsonify(**resposta)
            codigo=str(100000+secrets.randbelow(900000));hash_codigo=resumo_codigo(email,finalidade,codigo)
            c.execute('''INSERT INTO codigos_auth(email,codigo,expiracao,finalidade,tentativas,enviado_em) VALUES(%s,%s,%s,%s,0,CURRENT_TIMESTAMP)
             ON CONFLICT(email) DO UPDATE SET codigo=EXCLUDED.codigo,expiracao=EXCLUDED.expiracao,finalidade=EXCLUDED.finalidade,tentativas=0,enviado_em=CURRENT_TIMESTAMP''',(email,hash_codigo,datetime.now()+timedelta(minutes=10),finalidade));conn.commit()
            from services.email_service import enviar_confirmacao
            if not enviar_confirmacao(email,codigo,finalidade):
                c.execute('DELETE FROM codigos_auth WHERE email=%s AND codigo=%s',(email,hash_codigo));conn.commit()
                return jsonify(success=False,message='O envio está indisponível. Tente novamente mais tarde.'),503
            return jsonify(**resposta)
        if acao=='login':
            if not limitar(c,email,'login',8):conn.commit();return jsonify(success=False,message='Muitas tentativas. Aguarde 15 minutos.'),429
            conn.commit();c.execute('SELECT nome,email,rm,senha_hash FROM alunos WHERE email=%s FOR UPDATE',(email,));a=c.fetchone()
            correto=check_password_hash(a['senha_hash'] if a else DUMMY_HASH,senha)
            if not a or not correto:return jsonify(success=False,message='Credenciais incorretas.'),401
            # Emite antes de liberar a linha: um reset concorrente sempre revoga este token.
            token=gerar_token_aluno(email,a['nome'],a['rm'])
            c.execute('DELETE FROM auth_limites WHERE chave=%s',(resumo_codigo(email,'limite','login'),));conn.commit()
            return jsonify(success=True,token=token,aluno={k:a[k] for k in ('nome','email','rm')})
        if not verificar_codigo(c,email,'cadastro' if acao=='cadastrar' else 'recuperacao',d.get('codigo')):
            conn.commit();return jsonify(success=False,message='Código inválido, expirado ou bloqueado. Solicite um novo código.'),400
        if acao=='cadastrar':
            c.execute('SELECT email FROM alunos WHERE email=%s',(email,))
            if c.fetchone():return jsonify(success=False,message='Não foi possível criar a conta com estes dados.'),400
            c.execute('INSERT INTO alunos(email,nome,rm,senha_hash) VALUES(%s,%s,%s,%s)',(email,nome,rm,generate_password_hash(senha)))
            registrar_aceite(c,email)
        else:
            c.execute('UPDATE alunos SET senha_hash=%s WHERE email=%s',(generate_password_hash(senha),email))
            c.execute('''INSERT INTO auth_revogacoes(email,desde) VALUES(%s,%s) ON CONFLICT(email) DO UPDATE SET desde=EXCLUDED.desde''',(email,time.time()))
            c.execute('DELETE FROM auth_limites WHERE chave=%s',(resumo_codigo(email,'limite','login'),))
        token=gerar_token_aluno(email,nome,rm) if acao=='cadastrar' else None
        c.execute('DELETE FROM codigos_auth WHERE email=%s',(email,));conn.commit()
        if acao=='redefinir':return jsonify(success=True,message='Senha redefinida. Entre novamente em seus dispositivos.')
        return jsonify(success=True,token=token,aluno=dict(email=email,nome=nome,rm=rm))
    except Exception:
        if conn:conn.rollback()
        current_app.logger.warning('Operação de autenticação indisponível.')
        return jsonify(success=False,message='Não foi possível concluir a operação. Tente novamente.'),503
    finally:
        if conn:conn.close()


def administrador(conectar,email_config,senha_hash,senha_plana):
    from utils.security import gerar_token_secretaria
    d=request.get_json(silent=True)
    if not isinstance(d,dict):return jsonify(success=False,message='Credenciais inválidas.'),401
    email,senha=d.get('email'),d.get('senha')
    if not isinstance(email,str) or not isinstance(senha,str) or not 1<=len(senha)<=128:return jsonify(success=False,message='Credenciais inválidas.'),401
    email=email.strip().lower()
    if email!=email_config:
        check_password_hash(DUMMY_HASH,senha);return jsonify(success=False,message='Credenciais inválidas.'),401
    conn=None
    try:
        conn=conectar();c=conn.cursor(cursor_factory=RealDictCursor)
        if not limitar(c,email,'admin',8):conn.commit();return jsonify(success=False,message='Muitas tentativas. Aguarde 15 minutos.'),429
        conn.commit()
        try:correto=check_password_hash(senha_hash,senha) if senha_hash else bool(senha_plana) and hmac.compare_digest(senha.encode(),senha_plana.encode())
        except (ValueError,TypeError):correto=False
        if not correto:return jsonify(success=False,message='Credenciais inválidas.'),401
        c.execute('DELETE FROM auth_limites WHERE chave=%s',(resumo_codigo(email,'limite','admin'),));conn.commit()
        return jsonify(success=True,token=gerar_token_secretaria(email))
    except Exception:return jsonify(success=False,message='Não foi possível validar o acesso.'),503
    finally:
        if conn:conn.close()
