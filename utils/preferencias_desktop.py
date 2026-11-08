"""Somente filtros e larguras locais; nunca persiste sessão ou senha."""
import hashlib,json,os,tempfile
from pathlib import Path


def caminho(email):
    raiz=Path(os.environ.get('ETEC_PREFERENCIAS_DIR') or Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'etec-achados')
    return raiz/(hashlib.sha256(str(email).lower().encode()).hexdigest()+'.json')


def ler(email):
    try:
        p=caminho(email)
        if p.stat().st_size>4096:return {}
        dados=json.loads(p.read_text(encoding='utf-8'))
        return validar(dados)
    except (OSError,ValueError,TypeError):return {}


def validar(dados):
    if not isinstance(dados,dict):return {}
    filtros=dados.get('filtros',{})
    filtros={k:v[:maximo] for k,maximo in [('q',120),('categoria',50),('local',100),('inicio',10),('fim',10),('status',30)]
        if isinstance(filtros,dict) and isinstance(v:=filtros.get(k),str)}
    larguras=dados.get('larguras',{})
    larguras={str(k)[:30]:max(50,min(v,600)) for k,v in list(larguras.items())[:8] if isinstance(v,int)} if isinstance(larguras,dict) else {}
    return {'filtros':filtros,'larguras':larguras}


def salvar(email,dados):
    p=caminho(email);temporario=None
    try:
        p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=p.parent,delete=False) as arquivo:
            temporario=arquivo.name;json.dump(validar(dados),arquivo,ensure_ascii=False)
        os.replace(temporario,p);return True
    except OSError:return False
    finally:
        if temporario:
            try:Path(temporario).unlink(missing_ok=True)
            except OSError:pass
