"""Preparação exclusiva do ambiente de testes do devcontainer; não usa banco externo."""
import argparse,json,os,secrets,socket,subprocess,sys,time
from pathlib import Path

RAIZ=Path(__file__).resolve().parents[1]
ARQUIVO=RAIZ/'.devcontainer'/'.env.codespaces.json'
BANCO='postgresql://etec:etec-apenas-testes@db:5432/achados_testes'
CONTAS=[('aluno@aluno.cps.sp.gov.br','Aluno de demonstração','90001'),
        ('colega@aluno.cps.sp.gov.br','Outro aluno de demonstração','90002'),
        ('professor@etec.sp.gov.br','Professor de demonstração','PROFESSOR')]


def configurar():
    if os.environ.get('ETEC_CODESPACES_TESTE')!='1':
        raise RuntimeError('Use este comando dentro do Codespace/devcontainer de testes.')
    if not ARQUIVO.exists():
        dados={'jwt':secrets.token_urlsafe(48),'senha':secrets.token_urlsafe(18)}
        try:
            with open(ARQUIVO,'x',opener=lambda p,f:os.open(p,f,0o600)) as arquivo:json.dump(dados,arquivo)
        except FileExistsError:pass
    dados=json.loads(ARQUIVO.read_text())
    if not isinstance(dados.get('jwt'),str) or len(dados['jwt'])<32 or not isinstance(dados.get('senha'),str) or len(dados['senha'])<16:
        raise RuntimeError('Configuração local de testes inválida.')
    # Sempre substitui DATABASE_URL herdada; o script nunca escolhe um banco da escola.
    from werkzeug.security import generate_password_hash
    os.environ.update(DATABASE_URL=BANCO,DATABASE_SSLMODE='disable',JWT_SECRET=dados['jwt'],
                      ADMIN_EMAIL='secretaria@etec.sp.gov.br',ADMIN_SENHA='',
                      ADMIN_SENHA_HASH=generate_password_hash(dados['senha']),PORT='5000')
    return dados


def esperar_banco():
    import psycopg2
    for tentativa in range(30):
        try:
            with psycopg2.connect(BANCO,sslmode='disable',connect_timeout=2):pass
            break
        except psycopg2.OperationalError:
            if tentativa==29:raise RuntimeError('O banco de testes não iniciou. Confira o serviço db no Codespace.') from None
            time.sleep(1)


def preparar():
    dados=configurar()
    esperar_banco()
    sys.path.insert(0,str(RAIZ))
    import server
    # server já cria/aplica o esquema na importação; a consulta abaixo confirma o resultado.
    from werkzeug.security import generate_password_hash
    with server.get_db_connection() as conn:
        with conn.cursor() as c:
            c.execute('SELECT pg_advisory_xact_lock(285000001)')
            for email,nome,rm in CONTAS:
                c.execute('INSERT INTO alunos(email,nome,rm,senha_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(email) DO NOTHING',
                          (email,nome,rm,generate_password_hash(dados['senha'])))
            for nome,categoria,local in [('Garrafa azul · demonstração','OUTROS','Pátio'),('Caderno · demonstração','ESCOLARES','Biblioteca')]:
                c.execute('''INSERT INTO itens(nome_item,descricao,categoria,data_encontrado,local_encontrado,status,aprovado)
                 SELECT %s,'Objeto fictício para testar o portal.',%s,to_char(CURRENT_DATE,'DD/MM/YYYY'),%s,'DISPONÍVEL',TRUE
                 WHERE NOT EXISTS(SELECT 1 FROM itens WHERE nome_item=%s)''',(nome,categoria,local,nome))
    print('Banco de testes preparado. Para ver os acessos: python .devcontainer/ambiente.py contas')


def iniciar():
    preparar()
    with socket.socket() as porta:
        if porta.connect_ex(('127.0.0.1',5000))==0:
            print('A porta 5000 já está em uso. Abra a aba Ports/Portas.');return
    log=RAIZ/'.devcontainer'/'.env.codespaces.log'
    with open(log,'ab',opener=lambda p,f:os.open(p,f,0o600)) as saida:
        processo=subprocess.Popen([sys.executable,'-m','gunicorn','--workers','1','--threads','4','--timeout','60','--bind','0.0.0.0:5000','server:app'],
                                 cwd=RAIZ,env=dict(os.environ),stdout=saida,stderr=subprocess.STDOUT,start_new_session=True)
    for _ in range(50):
        if processo.poll() is not None:raise RuntimeError('O site não iniciou. Consulte .devcontainer/.env.codespaces.log.')
        with socket.socket() as porta:
            if porta.connect_ex(('127.0.0.1',5000))==0:
                print('Site iniciado. Na aba Ports/Portas, abra a porta 5000.');return
        time.sleep(.2)
    raise RuntimeError('O início demorou. Consulte .devcontainer/.env.codespaces.log antes de tentar novamente.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('acao',choices=['preparar','iniciar','contas']);args=parser.parse_args()
    os.chdir(RAIZ)
    if args.acao=='contas':
        dados=configurar()
        print('Somente demonstração. Mantenha a porta 5000 privada no Codespaces.')
        for email in ['secretaria@etec.sp.gov.br',*[c[0] for c in CONTAS]]:print(email)
        print('Senha de todas as contas de demonstração:',dados['senha'])
    elif args.acao=='preparar':preparar()
    else:iniciar()


if __name__=='__main__':
    try:main()
    except (RuntimeError,ValueError,OSError) as erro:raise SystemExit(str(erro)) from None
